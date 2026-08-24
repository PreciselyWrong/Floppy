from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from app.models import MediaTypes
from users import home_screen
from users.models import HomePinnedItem


class HomeUpNextTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(
            get_enabled_media_types=lambda: [
                MediaTypes.TV.value,
                MediaTypes.ANIME.value,
            ]
        )

    def test_ready_episode_is_selected_from_latest_active_title(self):
        season = SimpleNamespace(item=SimpleNamespace(season_number=1))
        item = SimpleNamespace(id=1, media_type=MediaTypes.TV.value, title="The Show")
        media = SimpleNamespace(
            item=item,
            item_id=item.id,
            progressed_at=timezone.now(),
            next_episode_target=lambda: (season, 3),
        )

        with (
            patch.object(HomePinnedItem.objects, "filter", return_value=[]),
            patch.object(
                home_screen.BasicMedia.objects,
                "get_media_list",
                side_effect=lambda _user, media_type, *_args, **_kwargs: (
                    [media] if media_type == MediaTypes.TV.value else []
                ),
            ),
        ):
            entries = home_screen._up_next_entries(self.user)

        self.assertEqual(len(entries), 1)
        self.assertIs(entries[0].item, item)
        self.assertIs(entries[0].media, media)
        self.assertEqual(entries[0].subtitle_override, "S01E03")
        self.assertTrue(entries[0].resume_navigation)
        self.assertIs(entries[0].title_item_override, item)

    def test_announced_release_is_used_when_no_episode_is_ready(self):
        release = timezone.now() + timedelta(days=2)
        item = SimpleNamespace(id=1, media_type=MediaTypes.ANIME.value, title="The Anime")
        media = SimpleNamespace(
            item=item,
            item_id=item.id,
            progressed_at=timezone.now(),
            next_episode_target=lambda: None,
        )

        with (
            patch.object(HomePinnedItem.objects, "filter", return_value=[]),
            patch.object(
                home_screen.BasicMedia.objects,
                "get_media_list",
                side_effect=lambda _user, media_type, *_args, **_kwargs: (
                    [media] if media_type == MediaTypes.ANIME.value else []
                ),
            ),
            patch.object(
                home_screen.BasicMedia.objects,
                "_next_episode_air_date_value",
                return_value=release,
            ),
        ):
            entries = home_screen._up_next_entries(self.user)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].subtitle_override, release)

    def test_pins_are_ordered_before_and_deduplicated_from_automatic_resume(self):
        now = timezone.now()
        pinned_item = SimpleNamespace(
            id=1,
            media_type=MediaTypes.TV.value,
            title="Pinned Show",
        )
        automatic_item = SimpleNamespace(
            id=2,
            media_type=MediaTypes.TV.value,
            title="Automatic Show",
        )
        season = SimpleNamespace(item=SimpleNamespace(season_number=1))
        pinned_media = SimpleNamespace(
            item=pinned_item,
            item_id=1,
            progressed_at=now - timedelta(days=2),
            next_episode_target=lambda: (season, 2),
        )
        automatic_media = SimpleNamespace(
            item=automatic_item,
            item_id=2,
            progressed_at=now,
            next_episode_target=lambda: (season, 4),
        )
        pins = [SimpleNamespace(item_id=1)]

        with (
            patch.object(
                HomePinnedItem.objects,
                "filter",
                return_value=pins,
            ),
            patch.object(
                home_screen.BasicMedia.objects,
                "get_media_list",
                side_effect=lambda _user, media_type, *_args, **_kwargs: (
                    [automatic_media, pinned_media]
                    if media_type == MediaTypes.TV.value
                    else []
                ),
            ),
        ):
            entries = home_screen._up_next_entries(self.user)

        self.assertEqual(
            [entry.item.title for entry in entries],
            ["Pinned Show", "Automatic Show"],
        )

    def test_season_resume_title_targets_the_parent_series(self):
        series_item = SimpleNamespace(media_type=MediaTypes.TV.value)
        season_item = SimpleNamespace(media_type=MediaTypes.SEASON.value)
        media = SimpleNamespace(
            related_tv=SimpleNamespace(item=series_item),
        )

        resume_navigation, title_item = home_screen._resume_navigation_metadata(
            season_item,
            media,
            ["In progress"],
        )

        self.assertTrue(resume_navigation)
        self.assertIs(title_item, series_item)
