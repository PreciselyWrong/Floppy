from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PublicReviewPreferenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="review-preferences-user",
            password="secret",
        )
        self.client.force_login(self.user)

    def test_preferences_persist_review_visibility_and_position(self):
        response = self.client.post(
            reverse("preferences"),
            {"show_public_reviews": "0", "public_reviews_position": "top"},
        )

        self.assertRedirects(response, reverse("preferences"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.show_public_reviews)
        self.assertEqual("top", self.user.public_reviews_position)

    def test_preferences_render_review_controls(self):
        response = self.client.get(reverse("preferences"))

        self.assertContains(response, "Public reviews")
        self.assertContains(response, 'name="public_reviews_position"')
