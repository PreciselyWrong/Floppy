import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.appearance import default_detail_layouts


class PublicReviewPreferenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="review-preferences-user",
            password="secret",
        )
        self.client.force_login(self.user)

    def test_appearance_persists_review_visibility_and_order(self):
        layouts = default_detail_layouts()
        layouts["episode"]["content"] = ["reviews", "notes", "cast"]

        response = self.client.post(
            reverse("appearance"),
            {
                "theme": "system",
                "custom_theme": "{}",
                "detail_layouts": json.dumps(layouts),
            },
        )

        self.assertRedirects(response, reverse("appearance"))
        self.user.refresh_from_db()
        self.assertEqual(
            ["reviews", "notes", "cast"],
            self.user.detail_page_layouts["episode"]["content"],
        )

    def test_review_controls_only_render_in_appearance(self):
        appearance = self.client.get(reverse("appearance"))
        preferences = self.client.get(reverse("preferences"))

        self.assertContains(appearance, "Public reviews")
        self.assertNotContains(preferences, 'name="show_public_reviews"')
        self.assertNotContains(preferences, 'name="public_reviews_position"')
