"""Regression coverage for combined upstream and private Home settings."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import HOME_ALL_MEDIA_TYPE, HomeScreenRow, HomeScreenRowTypeChoices


class UpstreamSyncHomeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="sync-home")
        self.client.force_login(self.user)

    def test_music_mode_and_private_journal_options_survive_settings_round_trip(self):
        music = HomeScreenRow.objects.create(
            user=self.user,
            media_type="music",
            row_type=HomeScreenRowTypeChoices.RECENTLY_UNRATED,
            filters={"recent_show": "all"},
        )
        journal = HomeScreenRow.objects.create(
            user=self.user,
            media_type=HOME_ALL_MEDIA_TYPE,
            row_type=HomeScreenRowTypeChoices.WATCH_HISTORY,
            filters={"binge_grouping": False, "media_types": ["movie"]},
            open_last_episode=False,
        )
        response = self.client.get(reverse("home_screen"))
        self.assertEqual(response.status_code, 200)
        sections = json.loads(response.context["home_screen_sections_json"])
        rows = {row["id"]: row for section in sections for row in section["rows"]}
        self.assertEqual(rows[music.pk]["recent_show"], "all")
        self.assertFalse(rows[journal.pk]["filters"]["binge_grouping"])
        self.assertFalse(rows[journal.pk]["open_last_episode"])
        response = self.client.post(
            reverse("home_screen"),
            {
                "home_screen_sections": json.dumps(sections),
                "show_media_type_headers": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        music = HomeScreenRow.objects.get(user=self.user, media_type="music")
        journal = HomeScreenRow.objects.get(
            user=self.user, media_type=HOME_ALL_MEDIA_TYPE
        )
        self.assertEqual(music.filters, {"recent_show": "all"})
        self.assertFalse(journal.filters["binge_grouping"])
        self.assertFalse(journal.open_last_episode)

    def test_home_settings_save_when_video_is_enabled(self):
        self.user.video_enabled = True
        self.user.save(update_fields=["video_enabled"])
        response = self.client.get(reverse("home_screen"))
        sections = json.loads(response.context["home_screen_sections_json"])
        video = next(
            section for section in sections if section["media_type"] == "video"
        )
        video["rows"][0]["custom_title"] = "Saved video row"
        response = self.client.post(
            reverse("home_screen"),
            {
                "home_screen_sections": json.dumps(sections),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            HomeScreenRow.objects.get(user=self.user, media_type="video").title,
            "Saved video row",
        )
