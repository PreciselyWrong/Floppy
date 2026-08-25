import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import MediaTypes
from users import home_screen
from users.models import HomeScreenRow, HomeScreenRowTypeChoices


class HomeHistoryRowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="home-history",
            password="test-password",
        )

    def _row(self):
        return HomeScreenRow.objects.create(
            user=self.user,
            media_type=MediaTypes.MOVIE.value,
            row_type=HomeScreenRowTypeChoices.HISTORY,
            sort_by="recent",
            direction="desc",
        )

    @patch("users.home_screen.get_recent_history_entries")
    def test_history_row_builds_a_bounded_incremental_batch(self, recent_entries):
        entries = [{"entry_key": str(index)} for index in range(14)]
        recent_entries.return_value = (entries, True)
        row = self._row()

        section = home_screen._build_row_section(
            self.user,
            row,
            MediaTypes.MOVIE.value,
            items_limit=14,
            batch_start=28,
        )

        recent_entries.assert_called_once_with(
            self.user,
            MediaTypes.MOVIE.value,
            limit=14,
            offset=28,
        )
        self.assertEqual(section["items"], entries)
        self.assertEqual(section["loaded_count"], 42)
        self.assertEqual(section["total"], 43)
        self.assertEqual(
            section["grid_template"],
            "app/components/home_history_grid.html",
        )
        self.assertEqual(section["url"], reverse("history") + "?media_type=movie")

    @patch("users.home_screen.get_recent_history_entries", return_value=([], False))
    def test_stale_history_offset_returns_terminal_pagination_metadata(
        self, _recent_entries
    ):
        row = self._row()

        section = home_screen._build_row_section(
            self.user,
            row,
            MediaTypes.MOVIE.value,
            items_limit=14,
            batch_start=999,
        )

        self.assertEqual(section["items"], [])
        self.assertEqual(section["loaded_count"], 999)
        self.assertEqual(section["total"], 999)

    def test_configuration_rejects_duplicate_history_rows_in_one_section(self):
        row_payload = {
            "enabled": True,
            "row_type": HomeScreenRowTypeChoices.HISTORY,
            "custom_title": "",
        }
        payload = json.dumps(
            [
                {
                    "media_type": MediaTypes.MOVIE.value,
                    "rows": [row_payload, row_payload],
                }
            ]
        )

        with self.assertRaisesMessage(
            home_screen.HomeScreenValidationError,
            "Only one 'History' row is allowed for movie.",
        ):
            home_screen.save_home_screen_configuration(self.user, payload)

    def test_settings_offer_history_as_a_configurable_row(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home_screen"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "History Row")

    @patch("users.home_screen.get_recent_history_entries")
    def test_htmx_pagination_renders_history_cards_and_progress_headers(
        self, recent_entries
    ):
        row = self._row()
        recent_entries.return_value = (
            [
                {
                    "media_type": MediaTypes.MOVIE.value,
                    "item": {
                        "media_type": MediaTypes.MOVIE.value,
                        "media_id": "history-movie",
                        "source": "manual",
                        "title": "History Movie",
                    },
                    "poster": "",
                    "title": "History Movie",
                    "display_title": "History Movie",
                    "played_at_local": timezone.now(),
                    "runtime_minutes": 90,
                    "runtime_display": "1h 30min",
                    "entry_key": "history-movie-1",
                }
            ],
            False,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("home") + f"?load_row={row.id}&offset=0",
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "app/components/home_history_grid.html",
        )
        self.assertContains(response, "History Movie")
        self.assertEqual(response.headers["X-Home-Row-Total"], "1")
        self.assertEqual(response.headers["X-Home-Row-Loaded"], "1")
