from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from app.models import MediaTypes
from users import home_screen


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
        item = SimpleNamespace(media_type=MediaTypes.TV.value, title="The Show")
        media = SimpleNamespace(
            item=item,
            progressed_at=timezone.now(),
            next_episode_target=lambda: (season, 3),
        )

        with patch.object(
            home_screen.BasicMedia.objects,
            "get_media_list",
            side_effect=lambda _user, media_type, *_args, **_kwargs: (
                [media] if media_type == MediaTypes.TV.value else []
            ),
        ):
            entries = home_screen._up_next_entries(self.user)

        self.assertEqual(len(entries), 1)
        self.assertIs(entries[0].item, item)
        self.assertIs(entries[0].media, media)
        self.assertEqual(entries[0].subtitle_override, "S01E03")

    def test_announced_release_is_used_when_no_episode_is_ready(self):
        release = timezone.now() + timedelta(days=2)
        item = SimpleNamespace(media_type=MediaTypes.ANIME.value, title="The Anime")
        media = SimpleNamespace(
            item=item,
            progressed_at=timezone.now(),
            next_episode_target=lambda: None,
        )

        with (
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
