from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.models import Item, MediaTypes, Sources, Status, TV
from users.models import HomePinnedItem


class HomePinTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="home-pin-user",
            password="test-pass",
        )
        self.item = Item.objects.create(
            title="Pinned Show",
            media_id="home-pinned-show",
            media_type=MediaTypes.TV.value,
            source=Sources.TMDB.value,
        )
        self.tracker = TV.objects.create(
            user=self.user,
            item=self.item,
            status=Status.IN_PROGRESS.value,
        )
        self.client.force_login(self.user)

    def test_toggle_pin_preserves_tracking_status(self):
        url = reverse("toggle_home_pin", args=[self.item.id])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            HomePinnedItem.objects.filter(user=self.user, item=self.item).exists()
        )
        self.assertContains(response, "Remove from Up Next")
        self.tracker.refresh_from_db()
        self.assertEqual(self.tracker.status, Status.IN_PROGRESS.value)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            HomePinnedItem.objects.filter(user=self.user, item=self.item).exists()
        )
        self.assertContains(response, "Pin to Up Next")
        self.tracker.refresh_from_db()
        self.assertEqual(self.tracker.status, Status.IN_PROGRESS.value)

    def test_pin_is_private_to_each_user(self):
        other_user = get_user_model().objects.create_user(
            username="other-home-pin-user",
            password="test-pass",
        )
        HomePinnedItem.objects.create(user=other_user, item=self.item)

        self.client.post(reverse("toggle_home_pin", args=[self.item.id]))

        self.assertTrue(
            HomePinnedItem.objects.filter(user=other_user, item=self.item).exists()
        )
        self.assertTrue(
            HomePinnedItem.objects.filter(user=self.user, item=self.item).exists()
        )
