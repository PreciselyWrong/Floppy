from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from app.public_reviews import PublicReview, ReviewFeed, ReviewProblem, ReviewProvider


@override_settings(BETASERIES_API_KEY="", TMDB_API="tmdb-key")
class PublicReviewViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="review-view-user",
            password="secret",
        )
        self.client.force_login(self.user)
        self.kwargs = {
            "source": "tmdb",
            "media_type": "movie",
            "media_id": "603",
            "title": "the-matrix",
        }

    @patch("app.public_review_views.collect_reviews")
    def test_preview_renders_only_two_reviews_and_links_to_full_screen(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[
                PublicReview("TMDB", "Alice", "First"),
                PublicReview("TMDB", "Bob", "Second"),
                PublicReview("TMDB", "Carla", "Third"),
            ],
            problems=[],
            any_provider_active=True,
        )

        response = self.client.get(reverse("public_reviews_preview", kwargs=self.kwargs))

        self.assertContains(response, "Alice")
        self.assertContains(response, "Bob")
        self.assertNotContains(response, "Carla")
        self.assertContains(response, "See all 3 reviews")

    @patch("app.public_review_views.collect_reviews")
    def test_preview_preserves_episode_and_catalogue_identity_in_full_link(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[PublicReview("BetaSeries", "Alice", "First")],
            problems=[],
            any_provider_active=True,
        )

        response = self.client.get(
            reverse("public_reviews_preview", kwargs=self.kwargs),
            {"season": "2", "episode": "3", "tvdb_id": "81189"},
        )

        self.assertContains(response, "season=2&amp;episode=3&amp;tvdb_id=81189")

    @patch("app.public_review_views.collect_reviews")
    def test_full_screen_applies_requested_sort(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[
                PublicReview("TMDB", "Best", "Great", score=9),
                PublicReview("TMDB", "Worst", "Bad", score=2),
            ],
            problems=[],
            any_provider_active=True,
        )

        response = self.client.get(
            reverse("public_reviews", kwargs=self.kwargs),
            {"sort": "worst"},
        )

        self.assertLess(response.content.index(b"Worst"), response.content.index(b"Best"))
        self.assertContains(response, "Lowest rated")

    @patch("app.public_review_views.collect_reviews")
    def test_full_screen_contains_long_book_reviews_on_mobile(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[
                PublicReview(
                    "Hardcover",
                    "A-reader-name-without-breaks" * 5,
                    "Averylongwordwithoutanybreaks" * 20,
                    score=10,
                )
            ],
            problems=[],
            any_provider_active=True,
        )

        response = self.client.get(reverse("public_reviews", kwargs=self.kwargs))

        self.assertContains(response, 'class="min-w-0 max-w-full overflow-hidden')
        self.assertContains(response, "[overflow-wrap:anywhere]")
        self.assertContains(response, "overflow-x-hidden")

    @patch("app.public_review_views.collect_reviews")
    def test_full_screen_sort_links_preserve_episode_identity(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[
                PublicReview("BetaSeries", "Alice", "First", score=8),
                PublicReview("BetaSeries", "Bob", "Second", score=6),
            ],
            problems=[],
            any_provider_active=True,
        )

        response = self.client.get(
            reverse("public_reviews", kwargs=self.kwargs),
            {"season": "2", "episode": "3", "tvdb_id": "81189"},
        )

        self.assertContains(
            response,
            "season=2&amp;episode=3&amp;tvdb_id=81189&amp;sort=best",
        )

    @patch("app.public_review_views.collect_reviews")
    def test_empty_and_provider_failure_are_distinct(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[],
            problems=[ReviewProblem("TMDB", "offline")],
            any_provider_active=True,
        )

        response = self.client.get(reverse("public_reviews_preview", kwargs=self.kwargs))

        self.assertContains(response, "TMDB reviews couldn't load")
        self.assertContains(response, "Retry")
        self.assertContains(response, "hx-get=")
        self.assertNotContains(response, "No public reviews yet")

    @patch("app.public_review_views.providers_for_target")
    @patch("app.public_review_views.collect_reviews")
    def test_full_screen_filters_by_provider_and_renders_attribution(
        self,
        collect,
        providers_for_target,
    ):
        providers_for_target.return_value = (
            ReviewProvider("TMDB", lambda *_: [], "https://www.themoviedb.org/", "img/tmdb-logo.png"),
            ReviewProvider("BetaSeries", lambda *_: [], "https://www.betaseries.com/"),
        )
        collect.return_value = ReviewFeed(
            reviews=[
                PublicReview("TMDB", "Alice", "TMDB review"),
                PublicReview("BetaSeries", "Bob", "BetaSeries review"),
            ],
            problems=[],
            any_provider_active=True,
            provider_counts={"TMDB": 12, "BetaSeries": 7},
        )

        response = self.client.get(
            reverse("public_reviews", kwargs=self.kwargs),
            {"provider": "TMDB"},
        )

        self.assertContains(response, "TMDB review")
        self.assertNotContains(response, "BetaSeries review")
        self.assertContains(response, "TMDB (12)")
        self.assertContains(response, "BetaSeries (7)")
        self.assertContains(response, "https://www.themoviedb.org/")
        self.assertContains(response, "tmdb-logo.png")

    @patch("app.public_review_views.collect_reviews")
    def test_full_screen_progressively_loads_and_replaces_the_review_feed(self, collect):
        collect.side_effect = [
            ReviewFeed(
                reviews=[PublicReview("TMDB", "Alice", "First page")],
                problems=[],
                any_provider_active=True,
                provider_counts={"TMDB": 21},
                has_more=True,
            ),
            ReviewFeed(
                reviews=[PublicReview("TMDB", "Bob", "Second page")],
                problems=[],
                any_provider_active=True,
                provider_counts={"TMDB": 21},
                has_more=False,
            ),
        ]

        response = self.client.get(
            reverse("public_reviews", kwargs=self.kwargs),
            {"page": "2"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "First page")
        self.assertContains(response, "Second page")
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.assertEqual([1, 2], [call.kwargs["page"] for call in collect.call_args_list])

    @patch("app.public_review_views.collect_reviews")
    def test_full_screen_offers_progressive_load_when_a_provider_has_more(self, collect):
        collect.return_value = ReviewFeed(
            reviews=[PublicReview("TMDB", "Alice", "First page")],
            problems=[],
            any_provider_active=True,
            provider_counts={"TMDB": 21},
            has_more=True,
        )

        response = self.client.get(reverse("public_reviews", kwargs=self.kwargs))

        self.assertContains(response, "Load more")
        self.assertContains(response, 'hx-target="#public-review-feed"')

    @patch("app.public_review_views.providers_for_target")
    @patch("app.public_review_views.collect_reviews")
    def test_selected_provider_hides_load_more_when_only_another_provider_has_more(
        self,
        collect,
        providers_for_target,
    ):
        providers_for_target.return_value = (
            ReviewProvider("TMDB", lambda *_: []),
            ReviewProvider("BetaSeries", lambda *_: []),
        )
        collect.return_value = ReviewFeed(
            reviews=[PublicReview("BetaSeries", "Alice", "First page")],
            problems=[],
            any_provider_active=True,
            provider_counts={"TMDB": 21, "BetaSeries": 1},
            has_more=True,
            provider_has_more={"TMDB": True, "BetaSeries": False},
        )

        response = self.client.get(
            reverse("public_reviews", kwargs=self.kwargs),
            {"provider": "BetaSeries"},
        )

        self.assertNotContains(response, "Load more")

    @patch("app.public_review_views.collect_reviews")
    def test_hidden_preview_does_not_call_providers(self, collect):
        self.user.show_public_reviews = False
        self.user.save(update_fields=["show_public_reviews"])

        response = self.client.get(reverse("public_reviews_preview", kwargs=self.kwargs))

        self.assertEqual(b"", response.content)
        collect.assert_not_called()
