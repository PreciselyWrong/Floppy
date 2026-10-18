import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from app.history_cache_reader import get_cached_history_window
from app.models import TV, Episode, Item, MediaTypes, Movie, Season, Sources, Status
from users import home_screen
from users.models import (
    HOME_ALL_MEDIA_TYPE,
    DirectionChoices,
    HomeScreenRow,
    HomeScreenRowTypeChoices,
    HomeSortChoices,
    MediaSortChoices,
)


def _episode(show_id, season, number, runtime=40):
    return {
        "media_type": MediaTypes.EPISODE.value,
        "item": {"source": "tmdb", "media_id": show_id, "media_type": "episode"},
        "show": {"id": int(show_id), "title": f"Show {show_id}"},
        "title": f"Show {show_id}",
        "season_number": season,
        "episode_number": number,
        "runtime_minutes": runtime,
    }


def _movie(title):
    return {"media_type": MediaTypes.MOVIE.value, "title": title, "runtime_minutes": 90}


class GroupJournalEntriesTests(SimpleTestCase):
    """Binge cards fold only consecutive episodes of one show."""

    def test_consecutive_episodes_of_one_show_become_one_card(self):
        items = home_screen.group_journal_entries(
            [_episode("1", 1, 3), _episode("1", 1, 2), _episode("1", 1, 1)],
            binge_grouping=True,
        )

        self.assertEqual(len(items), 1)
        group = items[0]
        self.assertTrue(group["is_group"])
        self.assertEqual(group["count"], 3)
        self.assertEqual(group["episode_range"], "S01E01-E03")
        self.assertEqual(group["series_title"], "Show 1")
        self.assertEqual(group["runtime_display"], "2h 00min")
        self.assertEqual(group["latest"]["episode_number"], 3)

    def test_other_activity_in_between_splits_the_run(self):
        items = home_screen.group_journal_entries(
            [
                _episode("1", 1, 4),
                _episode("1", 1, 3),
                _movie("Interlude"),
                _episode("1", 1, 2),
                _episode("2", 1, 1),
            ],
            binge_grouping=True,
        )

        self.assertEqual(
            [item["is_group"] for item in items],
            [True, False, False, False],
        )
        self.assertEqual(items[0]["count"], 2)
        self.assertEqual(items[1]["entry"]["title"], "Interlude")

    def test_run_across_seasons_has_no_single_range(self):
        items = home_screen.group_journal_entries(
            [_episode("1", 2, 1), _episode("1", 1, 10)],
            binge_grouping=True,
        )

        self.assertTrue(items[0]["is_group"])
        self.assertIsNone(items[0]["episode_range"])

    def test_grouping_off_keeps_every_entry(self):
        entries = [_episode("1", 1, 2), _episode("1", 1, 1)]

        items = home_screen.group_journal_entries(entries, binge_grouping=False)

        self.assertEqual(
            items,
            [{"is_group": False, "entry": entry} for entry in entries],
        )


class ActivityJournalSettingsTests(TestCase):
    """The journal row saves only the options it has."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="journal",
            password="testpass123",
        )

    def _save(self, media_type, row):
        payload = [{"media_type": media_type, "rows": [row]}]
        home_screen.save_home_screen_configuration(self.user, json.dumps(payload))
        return HomeScreenRow.objects.get(user=self.user, media_type=media_type)

    def test_all_media_accepts_the_journal_and_drops_unknown_options(self):
        row = self._save(
            HOME_ALL_MEDIA_TYPE,
            {
                "row_type": HomeScreenRowTypeChoices.WATCH_HISTORY,
                "sort_by": MediaSortChoices.TITLE,
                "direction": DirectionChoices.ASC,
                "filters": {"binge_grouping": False, "status": ["Completed"]},
            },
        )

        self.assertEqual(row.row_type, HomeScreenRowTypeChoices.WATCH_HISTORY)
        self.assertEqual(row.filters, {"binge_grouping": False})
        self.assertEqual(row.sort_by, HomeSortChoices.RECENT)
        self.assertEqual(row.direction, DirectionChoices.DESC)

        section = next(
            section
            for section in home_screen.serialize_settings_sections(self.user)
            if section["media_type"] == HOME_ALL_MEDIA_TYPE
        )
        self.assertEqual(section["rows"][0]["filters"], {"binge_grouping": False})
        self.assertEqual(section["rows"][0]["title"], "Activity Journal")

    def test_binge_grouping_defaults_on(self):
        row = self._save(
            MediaTypes.TV.value,
            {"row_type": HomeScreenRowTypeChoices.WATCH_HISTORY},
        )

        self.assertEqual(row.filters, {"binge_grouping": True})
        self.assertTrue(home_screen.journal_binge_grouping(row))

    def test_typed_journal_links_to_the_filtered_history(self):
        row = self._save(
            MediaTypes.TV.value,
            {"row_type": HomeScreenRowTypeChoices.WATCH_HISTORY},
        )
        all_row = HomeScreenRow(
            user=self.user,
            media_type=HOME_ALL_MEDIA_TYPE,
            row_type=HomeScreenRowTypeChoices.WATCH_HISTORY,
        )

        self.assertEqual(
            home_screen.home_row_destination_url(row, self.user),
            f"{reverse('history')}?media_type=tv",
        )
        self.assertEqual(
            home_screen.home_row_destination_url(all_row, self.user),
            reverse("history"),
        )


class ActivityJournalHomeTests(TestCase):
    """The journal renders recent History days on Home."""

    def setUp(self):
        cache.clear()
        credentials = {"username": "journal-home", "password": "testpass123"}
        self.user = get_user_model().objects.create_user(**credentials)
        self.client.login(**credentials)
        self.now = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        self.row = HomeScreenRow.objects.create(
            user=self.user,
            media_type=HOME_ALL_MEDIA_TYPE,
            position=0,
            row_type=HomeScreenRowTypeChoices.WATCH_HISTORY,
            sort_by=HomeSortChoices.RECENT,
            direction=DirectionChoices.DESC,
            filters={"binge_grouping": True},
        )

    def _warm_history(self):
        """Build the History index the way a History visit would.

        TestCase never commits, so the on_commit invalidation that follows each
        write in production never runs; start from a fresh index instead.
        """
        cache.clear()
        get_cached_history_window(self.user, limit=1, offset=0)

    def _watch_movie(self, title, minutes_ago):
        item = Item.objects.create(
            media_id=f"movie-{title}",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title=title,
            image="https://example.com/movie.jpg",
        )
        Movie.objects.create(
            item=item,
            user=self.user,
            status=Status.COMPLETED.value,
            end_date=self.now - timedelta(minutes=minutes_ago),
        )

    def _watch_episodes(self, title, numbers, minutes_ago, spacing_minutes=30):
        tv_item = Item.objects.create(
            media_id="show-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.TV.value,
            title=title,
            image="https://example.com/tv.jpg",
        )
        tv = TV.objects.create(
            item=tv_item,
            user=self.user,
            status=Status.IN_PROGRESS.value,
        )
        season_item = Item.objects.create(
            media_id="show-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.SEASON.value,
            title=title,
            image="https://example.com/season.jpg",
            season_number=1,
        )
        season = Season.objects.create(
            item=season_item,
            user=self.user,
            related_tv=tv,
            status=Status.IN_PROGRESS.value,
        )
        for offset, number in enumerate(numbers):
            episode_item = Item.objects.create(
                media_id="show-1",
                source=Sources.TMDB.value,
                media_type=MediaTypes.EPISODE.value,
                title=title,
                image="https://example.com/episode.jpg",
                season_number=1,
                episode_number=number,
            )
            Episode.objects.create(
                item=episode_item,
                related_season=season,
                end_date=self.now
                - timedelta(minutes=minutes_ago - offset * spacing_minutes),
            )

    def test_home_renders_days_with_a_binge_card(self):
        self._watch_movie("Journal Movie", minutes_ago=300)
        self._watch_episodes("Journal Show", [1, 2, 3], minutes_ago=200)
        self._warm_history()

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Activity Journal")
        self.assertContains(response, "Journal Movie")
        self.assertContains(response, "Journal Show")
        self.assertContains(response, "S01E01-E03")
        self.assertContains(response, "3 episodes")
        self.assertContains(response, f'href="{reverse("history")}"')

    def test_binge_grouping_off_lists_each_episode(self):
        self.row.filters = {"binge_grouping": False}
        self.row.save(update_fields=["filters"])
        self._watch_episodes("Journal Show", [1, 2, 3], minutes_ago=200)
        self._warm_history()

        groups = home_screen.build_home_page_groups(self.user, items_limit=14)
        journal = next(
            row for group in groups for row in group["rows"] if row.get("is_journal")
        )

        items = journal["days"][0]["items"]
        self.assertEqual(len(items), 3)
        self.assertFalse(any(item["is_group"] for item in items))
        self.assertEqual(journal["total"], journal["loaded_count"])

    def test_typed_journal_shows_only_its_media_type(self):
        self.row.media_type = MediaTypes.MOVIE.value
        self.row.save(update_fields=["media_type"])
        self._watch_movie("Journal Movie", minutes_ago=300)
        self._watch_episodes("Journal Show", [1, 2], minutes_ago=200)
        self._warm_history()

        section = home_screen._activity_journal_section(self.user, self.row)

        titles = [
            item["entry"]["title"] for day in section["days"] for item in day["items"]
        ]
        self.assertEqual(titles, ["Journal Movie"])

    def test_typed_journal_looks_past_the_first_window_of_days(self):
        self.row.media_type = MediaTypes.MOVIE.value
        self.row.save(update_fields=["media_type"])
        days = home_screen.ACTIVITY_JOURNAL_DAYS + 2
        self._watch_movie("Older Movie", minutes_ago=(days + 1) * 24 * 60)
        self._watch_episodes(
            "Daily Show",
            list(range(1, days + 1)),
            minutes_ago=days * 24 * 60,
            spacing_minutes=24 * 60,
        )
        self._warm_history()

        section = home_screen._activity_journal_section(self.user, self.row)

        self.assertEqual(
            [
                item["entry"]["title"]
                for day in section["days"]
                for item in day["items"]
            ],
            ["Older Movie"],
        )

    def test_cold_index_hides_the_row_and_builds_in_the_background(self):
        self._watch_movie("Journal Movie", minutes_ago=300)
        cache.clear()

        with (
            patch("app.history_cache_reader.build_history_index") as build_inline,
            patch("app.history_cache_reader.schedule_history_refresh") as schedule,
        ):
            section = home_screen._activity_journal_section(self.user, self.row)

        self.assertIsNone(section)
        build_inline.assert_not_called()
        schedule.assert_called_once()
        self.assertFalse(schedule.call_args.kwargs["allow_inline"])

    def test_cold_index_option_rejects_a_media_type_filter(self):
        with self.assertRaises(ValueError):
            get_cached_history_window(
                self.user,
                limit=1,
                offset=0,
                filters={"media_type": [MediaTypes.MOVIE.value]},
                build_cold_index=False,
            )

    def test_empty_history_hides_the_row(self):
        self._warm_history()
        self.assertIsNone(home_screen._activity_journal_section(self.user, self.row))
