from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.models import MediaTypes, Sources
from app.public_reviews import ReviewProvider


class PublicReviewDetailIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="public-review-detail-user",
            password="secret",
        )
        self.client.force_login(self.user)
        self.provider = ReviewProvider("Test", lambda *_: [])

    def _detail_url(self, source, media_type, media_id="238"):
        return reverse(
            "media_details",
            kwargs={
                "source": source,
                "media_type": media_type,
                "media_id": media_id,
                "title": "reviewed-title",
            },
        )

    @patch("app.media_details_views.providers_for_target")
    @patch("app.providers.services.get_media_metadata")
    def test_movie_detail_renders_the_lazy_review_loader(self, metadata, providers):
        providers.return_value = (self.provider,)
        metadata.return_value = {
            "media_id": "238",
            "title": "Reviewed Movie",
            "media_type": MediaTypes.MOVIE.value,
            "source": Sources.TMDB.value,
            "image": "https://example.com/movie.jpg",
            "synopsis": "Movie synopsis marker.",
            "details": {},
        }

        response = self.client.get(
            self._detail_url(Sources.TMDB.value, MediaTypes.MOVIE.value),
            {"fragment": "secondary"},
        )

        self.assertContains(response, "Loading public reviews")
        self.assertContains(
            response, 'data-detail-section="reviews" style="order: 5"'
        )

    @patch("app.media_details_views.providers_for_target")
    @patch("app.providers.services.get_media_metadata")
    def test_tv_detail_renders_the_lazy_review_loader(self, metadata, providers):
        providers.return_value = (self.provider,)
        metadata.return_value = {
            "media_id": "1399",
            "title": "Reviewed Show",
            "media_type": MediaTypes.TV.value,
            "source": Sources.TMDB.value,
            "image": "https://example.com/show.jpg",
            "synopsis": "Series synopsis marker.",
            "details": {},
            "seasons": [],
        }

        response = self.client.get(
            self._detail_url(Sources.TMDB.value, MediaTypes.TV.value, "1399"),
            {"fragment": "secondary"},
        )

        self.assertContains(response, "Loading public reviews")
        self.assertContains(
            response, 'data-detail-section="reviews" style="order: 6"'
        )

    @patch("app.media_details_views.providers_for_target")
    @patch("app.providers.services.get_media_metadata")
    def test_book_detail_renders_the_lazy_review_loader(self, metadata, providers):
        providers.return_value = (self.provider,)
        metadata.return_value = {
            "media_id": "312460",
            "title": "Reviewed Book",
            "media_type": MediaTypes.BOOK.value,
            "source": Sources.HARDCOVER.value,
            "image": "https://example.com/book.jpg",
            "synopsis": "Book synopsis marker.",
            "details": {},
        }

        response = self.client.get(
            self._detail_url(Sources.HARDCOVER.value, MediaTypes.BOOK.value, "312460"),
            {"fragment": "secondary"},
        )

        self.assertContains(response, "Loading public reviews")
        self.assertContains(
            response, 'data-detail-section="reviews" style="order: 5"'
        )

    @patch("app.views.providers_for_target")
    @patch("app.views.tmdb.episode", return_value={})
    @patch("app.providers.services.get_media_metadata")
    @patch("app.providers.tmdb.process_episodes", return_value=[])
    def test_episode_detail_renders_the_lazy_review_loader(
        self,
        _process_episodes,
        metadata,
        _episode,
        providers,
    ):
        providers.return_value = (self.provider,)
        metadata.return_value = {
            "media_id": "81189",
            "title": "Reviewed Show",
            "media_type": MediaTypes.TV.value,
            "source": Sources.TVDB.value,
            "image": "https://example.com/show.jpg",
            "provider_external_ids": {"tvdb_id": "81189"},
            "season/1": {
                "title": "Season 1",
                "season_title": "Season 1",
                "media_id": "81189",
                "media_type": MediaTypes.SEASON.value,
                "source": Sources.TVDB.value,
                "image": "https://example.com/season.jpg",
                "episodes": [],
            },
        }

        response = self.client.get(
            reverse(
                "episode_details",
                kwargs={
                    "source": Sources.TVDB.value,
                    "media_id": "81189",
                    "title": "reviewed-show",
                    "season_number": 1,
                    "episode_number": 1,
                },
            )
        )

        self.assertContains(response, "Loading public reviews")
        self.assertContains(
            response, 'data-detail-section="reviews" style="order: 3"'
        )
        self.assertContains(response, "season=1&amp;episode=1&amp;tvdb_id=81189")

    @patch("app.media_details_views.providers_for_target")
    @patch("app.providers.services.get_media_metadata")
    def test_saved_order_is_applied_to_the_detail_loader(self, metadata, providers):
        self.user.detail_page_layouts = {
            "media": {"content": ["reviews", "notes", "cast"]}
        }
        self.user.save(update_fields=["detail_page_layouts"])
        providers.return_value = (self.provider,)
        metadata.return_value = {
            "media_id": "238",
            "title": "Reviewed Movie",
            "media_type": MediaTypes.MOVIE.value,
            "source": Sources.TMDB.value,
            "image": "https://example.com/movie.jpg",
            "details": {},
        }

        response = self.client.get(
            self._detail_url(Sources.TMDB.value, MediaTypes.MOVIE.value),
            {"fragment": "secondary"},
        )

        self.assertContains(
            response, 'data-detail-section="reviews" style="order: 0"'
        )
