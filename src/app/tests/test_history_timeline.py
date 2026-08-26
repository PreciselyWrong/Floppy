from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app import history_timeline
from app.models import (
    TV,
    Book,
    Episode,
    Item,
    MediaTypes,
    Movie,
    Season,
    Sources,
    Status,
)


def _start_model_metadata_patches(test_case):
    mock_item_media_metadata = patch(
        "app.models.item.providers.services.get_media_metadata",
        return_value={"max_progress": 1},
    )
    mock_media_media_metadata = patch(
        "app.models.media.providers.services.get_media_metadata",
        return_value={"max_progress": 1},
    )
    mock_fetch_releases = patch("app.models.Item.fetch_releases")
    mock_item_media_metadata.start()
    mock_media_media_metadata.start()
    mock_fetch_releases.start()
    test_case.addCleanup(mock_item_media_metadata.stop)
    test_case.addCleanup(mock_media_media_metadata.stop)
    test_case.addCleanup(mock_fetch_releases.stop)


class PureHistoryTimelineGroupingTests(TestCase):
    """Test pure grouping, range, runtime, and show identity contracts."""

    def test_consecutive_same_show_episodes_group(self):
        show = {"source": "tmdb", "media_id": "100", "title": "Great Show"}
        now = timezone.now()
        ep3 = {
            "media_type": MediaTypes.EPISODE.value,
            "show": show,
            "title": "Ep 3",
            "display_title": "Ep 3",
            "season_number": 1,
            "episode_number": 3,
            "played_at_local": now,
            "runtime_minutes": 45,
            "score": 8,
            "poster": "http://example.com/ep3.jpg",
            "entry_key": "ep-3",
        }
        ep2 = {
            "media_type": MediaTypes.EPISODE.value,
            "show": show,
            "title": "Ep 2",
            "display_title": "Ep 2",
            "season_number": 1,
            "episode_number": 2,
            "played_at_local": now - timedelta(minutes=50),
            "runtime_minutes": 45,
            "score": 9,
            "poster": "http://example.com/ep2.jpg",
            "entry_key": "ep-2",
        }
        grouped = history_timeline.group_day_timeline_entries([ep3, ep2])
        self.assertEqual(len(grouped), 1)
        binge = grouped[0]
        self.assertTrue(binge["is_binge"])
        self.assertEqual(binge["count"], 2)
        self.assertEqual(binge["title"], "Great Show")
        self.assertEqual(binge["poster"], "http://example.com/ep3.jpg")
        self.assertEqual(binge["episode_range"], "S01E02\N{EN DASH}E03")
        self.assertEqual(binge["runtime_minutes"], 90)
        self.assertEqual(binge["runtime_display"], "1h 30min")
        self.assertEqual(len(binge["entries"]), 2)
        self.assertEqual(binge["entries"][0]["entry_key"], "ep-3")
        self.assertEqual(binge["entries"][1]["entry_key"], "ep-2")

    def test_different_show_episodes_do_not_group(self):
        show_a = {"source": "tmdb", "media_id": "100", "title": "Show A"}
        show_b = {"source": "tmdb", "media_id": "200", "title": "Show B"}
        now = timezone.now()
        ep_a = {
            "media_type": MediaTypes.EPISODE.value,
            "show": show_a,
            "title": "Show A Ep 1",
            "played_at_local": now,
            "entry_key": "a1",
        }
        ep_b = {
            "media_type": MediaTypes.EPISODE.value,
            "show": show_b,
            "title": "Show B Ep 1",
            "played_at_local": now - timedelta(minutes=50),
            "entry_key": "b1",
        }
        grouped = history_timeline.group_day_timeline_entries([ep_a, ep_b])
        self.assertEqual(len(grouped), 2)
        self.assertFalse(grouped[0]["is_binge"])
        self.assertFalse(grouped[1]["is_binge"])

    def test_non_consecutive_same_show_episodes_do_not_group(self):
        show_a = {"source": "tmdb", "media_id": "100", "title": "Show A"}
        now = timezone.now()
        ep1 = {
            "media_type": MediaTypes.EPISODE.value,
            "show": show_a,
            "title": "Ep 2",
            "played_at_local": now,
            "entry_key": "ep-2",
        }
        movie = {
            "media_type": MediaTypes.MOVIE.value,
            "title": "Movie In Between",
            "played_at_local": now - timedelta(hours=1),
            "entry_key": "mov-1",
        }
        ep2 = {
            "media_type": MediaTypes.EPISODE.value,
            "show": show_a,
            "title": "Ep 1",
            "played_at_local": now - timedelta(hours=3),
            "entry_key": "ep-1",
        }
        grouped = history_timeline.group_day_timeline_entries([ep1, movie, ep2])
        self.assertEqual(len(grouped), 3)
        self.assertFalse(grouped[0]["is_binge"])
        self.assertFalse(grouped[1]["is_binge"])
        self.assertFalse(grouped[2]["is_binge"])

    def test_movies_and_other_media_do_not_group(self):
        now = timezone.now()
        mov1 = {
            "media_type": MediaTypes.MOVIE.value,
            "title": "Movie 1",
            "played_at_local": now,
            "entry_key": "m1",
        }
        mov2 = {
            "media_type": MediaTypes.MOVIE.value,
            "title": "Movie 2",
            "played_at_local": now - timedelta(hours=2),
            "entry_key": "m2",
        }
        grouped = history_timeline.group_day_timeline_entries([mov1, mov2])
        self.assertEqual(len(grouped), 2)
        self.assertFalse(grouped[0]["is_binge"])
        self.assertFalse(grouped[1]["is_binge"])

    def test_episode_range_single_season_and_multi_season(self):
        entries_single = [
            {"season_number": 1, "episode_number": 2},
            {"season_number": 1, "episode_number": 5},
            {"season_number": 1, "episode_number": 3},
        ]
        self.assertEqual(
            history_timeline.format_episode_range(entries_single),
            "S01E02\N{EN DASH}E05",
        )

        entries_multi_season = [
            {"season_number": 1, "episode_number": 10},
            {"season_number": 2, "episode_number": 1},
        ]
        self.assertIsNone(history_timeline.format_episode_range(entries_multi_season))

        entries_missing_num = [
            {"season_number": 1, "episode_number": 1},
            {"season_number": 1, "episode_number": None},
        ]
        self.assertIsNone(history_timeline.format_episode_range(entries_missing_num))

    def test_total_runtime_calculation(self):
        # All known
        entries_known = [{"runtime_minutes": 45}, {"runtime_minutes": 55}]
        mins, display = history_timeline.calculate_total_runtime(entries_known)
        self.assertEqual(mins, 100)
        self.assertEqual(display, "1h 40min")

        # Unknown / None / Fallback
        entries_with_none = [{"runtime_minutes": 45}, {"runtime_minutes": None}]
        self.assertEqual(
            history_timeline.calculate_total_runtime(entries_with_none),
            (None, None),
        )

        entries_with_zero = [{"runtime_minutes": 45}, {"runtime_minutes": 0}]
        self.assertEqual(
            history_timeline.calculate_total_runtime(entries_with_zero),
            (None, None),
        )

        entries_with_unknown_aired = [
            {"runtime_minutes": 45},
            {"runtime_minutes": 999998},
        ]
        self.assertEqual(
            history_timeline.calculate_total_runtime(entries_with_unknown_aired),
            (None, None),
        )

    def test_timeline_families(self):
        self.assertEqual(history_timeline.get_timeline_family("movie"), "movies")
        self.assertEqual(history_timeline.get_timeline_family("tv"), "series")
        self.assertEqual(history_timeline.get_timeline_family("season"), "series")
        self.assertEqual(history_timeline.get_timeline_family("episode"), "series")
        self.assertEqual(history_timeline.get_timeline_family("book"), "books")
        self.assertEqual(history_timeline.get_timeline_family("comic"), "books")
        self.assertEqual(history_timeline.get_timeline_family("manga"), "books")
        self.assertEqual(history_timeline.get_timeline_family("game"), "other")
        self.assertEqual(history_timeline.get_timeline_family("music"), "other")


class HistoryTimelineViewTests(TestCase):
    """Test rendered HTML: chips, timeline classes, binge disclosures, and direct links."""

    def setUp(self):
        _start_model_metadata_patches(self)
        self.credentials = {"username": "timeline_user", "password": "password123"}
        self.user = get_user_model().objects.create_user(**self.credentials)
        self.client.login(**self.credentials)

        # Create a TV show with 2 consecutive episodes on the same day
        self.tv_item = Item.objects.create(
            media_id="tv-100",
            source=Sources.TMDB.value,
            media_type=MediaTypes.TV.value,
            title="Timeline Series",
            image="http://example.com/series.jpg",
        )
        self.tv = TV.objects.create(
            item=self.tv_item,
            user=self.user,
            status=Status.IN_PROGRESS.value,
        )
        self.season_item = Item.objects.create(
            media_id="season-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.SEASON.value,
            title="Season 1",
            season_number=1,
        )
        self.season = Season.objects.create(
            item=self.season_item,
            user=self.user,
            related_tv=self.tv,
        )

        now = timezone.now()
        self.ep1_item = Item.objects.create(
            media_id="ep-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="Pilot Episode",
            season_number=1,
            episode_number=1,
            runtime_minutes=42,
        )
        self.ep1 = Episode.objects.create(
            item=self.ep1_item,
            related_season=self.season,
            status=Status.COMPLETED.value,
            score=8,
            end_date=now - timedelta(minutes=45),
        )

        self.ep2_item = Item.objects.create(
            media_id="ep-2",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="Second Episode",
            season_number=1,
            episode_number=2,
            runtime_minutes=44,
        )
        self.ep2 = Episode.objects.create(
            item=self.ep2_item,
            related_season=self.season,
            status=Status.COMPLETED.value,
            score=9,
            end_date=now,
        )

        # Create a movie on the same day
        self.mov_item = Item.objects.create(
            media_id="mov-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title="Timeline Movie",
            image="http://example.com/movie.jpg",
            runtime_minutes=110,
        )
        self.movie = Movie.objects.create(
            item=self.mov_item,
            user=self.user,
            status=Status.COMPLETED.value,
            score=7,
            end_date=now - timedelta(hours=3),
        )

        book_item = Item.objects.create(
            media_id="book-1",
            source=Sources.MANUAL.value,
            media_type=MediaTypes.BOOK.value,
            title="Timeline Book",
            image="http://example.com/book.jpg",
        )
        self.book = Book.objects.create(
            item=book_item,
            user=self.user,
            status=Status.COMPLETED.value,
            score=6,
            end_date=now - timedelta(hours=4),
        )

    def test_history_page_renders_chips_and_timeline_structure(self):
        response = self.client.get(reverse("history"))
        self.assertEqual(response.status_code, 200)

        # Top chips: All, Movies, Series, Books
        self.assertContains(response, 'data-timeline-chip="all"', html=False)
        self.assertContains(response, 'data-timeline-chip="movies"', html=False)
        self.assertContains(response, 'data-timeline-chip="series"', html=False)
        self.assertContains(response, 'data-timeline-chip="books"', html=False)

        # Day entries must NOT use the legacy media-grid
        self.assertNotContains(response, 'class="media-grid"', html=False)
        self.assertContains(response, "history-day", html=False)

        # Binge disclosure and series header
        self.assertContains(response, "Timeline Series", html=False)
        self.assertContains(response, "S01E01\N{EN DASH}E02", html=False)
        self.assertContains(response, "Pilot Episode", html=False)
        self.assertContains(response, "Second Episode", html=False)

        # Direct episode links
        self.assertContains(
            response,
            reverse(
                "episode_details",
                kwargs={
                    "source": Sources.TMDB.value,
                    "media_id": "ep-1",
                    "title": "pilot-episode",
                    "season_number": 1,
                    "episode_number": 1,
                },
            ),
            html=False,
        )
        self.assertContains(response, 'data-timeline-family="movies"', html=False)
        self.assertContains(response, 'data-timeline-family="series"', html=False)
        self.assertContains(response, 'data-timeline-family="books"', html=False)
