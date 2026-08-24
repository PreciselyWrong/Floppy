import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.appearance import DETAIL_LAYOUT_FAMILIES
from users.templatetags.user_tags import detail_section_attrs


class AppearanceViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="appearance-user",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_appearance_exposes_presets_and_distinct_detail_families(self):
        response = self.client.get(reverse("appearance"))

        self.assertContains(response, "Projector")
        self.assertContains(response, "Video store")
        self.assertContains(response, "Custom palette")
        self.assertContains(response, "Episodes")
        self.assertContains(response, "Music albums")
        self.assertNotEqual(
            DETAIL_LAYOUT_FAMILIES["episode"]["zones"],
            DETAIL_LAYOUT_FAMILIES["music_album"]["zones"],
        )

    def test_appearance_persists_custom_palette_and_ordered_sections(self):
        layouts = {
            "media": {
                "sidebar": ["details", "genres"],
                "content": ["cast", "notes"],
            }
        }
        palette = {
            "page_bg": "#10141f",
            "surface": "#1b2233",
            "panel": "#202940",
            "text": "#f6f1df",
            "muted": "#adb7cc",
            "accent": "#ffb454",
        }

        response = self.client.post(
            reverse("appearance"),
            {
                "theme": "custom",
                "custom_theme": json.dumps(palette),
                "detail_layouts": json.dumps(layouts),
            },
        )

        self.assertRedirects(response, reverse("appearance"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "custom")
        self.assertEqual(self.user.custom_theme, palette)
        self.assertEqual(self.user.detail_page_layouts["media"], layouts["media"])

    def test_appearance_rejects_unknown_sections_without_partial_save(self):
        response = self.client.post(
            reverse("appearance"),
            {
                "theme": "projector",
                "custom_theme": "{}",
                "detail_layouts": json.dumps(
                    {"episode": {"content": ["notes", "not-a-section"]}}
                ),
            },
        )

        self.assertRedirects(response, reverse("appearance"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "system")
        self.assertEqual(self.user.detail_page_layouts, {})

    def test_custom_theme_is_rendered_as_safe_css_variables(self):
        self.user.theme = "custom"
        self.user.custom_theme = {
            "page_bg": "#10141f",
            "accent": "red; background:url(https://example.test)",
        }
        self.user.save(update_fields=["theme", "custom_theme"])

        response = self.client.get(reverse("preferences"))

        self.assertContains(response, "--color-page-bg: #10141f")
        self.assertNotContains(response, "background:url")

    def test_detail_section_attributes_apply_visibility_and_order(self):
        self.user.detail_page_layouts = {
            "episode": {"content": ["crew", "notes"]}
        }

        self.assertIn(
            'data-detail-section="crew" style="order: 0"',
            str(detail_section_attrs(self.user, "episode", "content", "crew")),
        )
        self.assertIn(
            'data-detail-section="notes" style="order: 1"',
            str(detail_section_attrs(self.user, "episode", "content", "notes")),
        )
        self.assertIn(
            'data-detail-section="cast" hidden',
            str(detail_section_attrs(self.user, "episode", "content", "cast")),
        )
