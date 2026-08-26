from datetime import UTC, datetime
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from app import public_reviews
from app.providers import betaseries, hardcover, tmdb


def review(author, *, published_at=None, score=None):
    return public_reviews.PublicReview(
        provider="test",
        author=author,
        body="A useful public review.",
        published_at=published_at,
        score=score,
    )


class PublicReviewSortTests(SimpleTestCase):
    def setUp(self):
        self.reviews = [
            review("Bob", published_at=datetime(2026, 1, 10, tzinfo=UTC), score=6),
            review("Alice", published_at=datetime(2026, 1, 20, tzinfo=UTC), score=9),
            review("Carla", published_at=datetime(2026, 1, 15, tzinfo=UTC), score=3),
        ]

    def test_supports_the_four_companion_sorts(self):
        expected = {
            "recent": ["Alice", "Carla", "Bob"],
            "oldest": ["Bob", "Carla", "Alice"],
            "best": ["Alice", "Bob", "Carla"],
            "worst": ["Carla", "Bob", "Alice"],
        }

        for sort, authors in expected.items():
            with self.subTest(sort=sort):
                self.assertEqual(
                    authors,
                    [item.author for item in public_reviews.sort_reviews(self.reviews, sort)],
                )

    def test_missing_sort_values_are_always_last(self):
        undated = review("Undated", score=5)
        unrated = review(
            "Unrated",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        self.assertEqual(
            "Undated",
            public_reviews.sort_reviews(self.reviews + [undated], "oldest")[-1].author,
        )
        self.assertEqual(
            "Unrated",
            public_reviews.sort_reviews(self.reviews + [unrated], "best")[-1].author,
        )


class PublicReviewFeedTests(SimpleTestCase):
    def test_one_provider_failure_does_not_hide_other_reviews(self):
        target = public_reviews.ReviewTarget("movie", "tmdb", "1")
        providers = (
            public_reviews.ReviewProvider("working", lambda *_: [review("Alice")]),
            public_reviews.ReviewProvider("broken", Mock(side_effect=RuntimeError("offline"))),
        )

        feed = public_reviews.collect_reviews(target, user=None, providers=providers)

        self.assertEqual(["Alice"], [item.author for item in feed.reviews])
        self.assertEqual(["broken"], [problem.provider for problem in feed.problems])

    def test_empty_active_provider_is_distinct_from_no_provider(self):
        target = public_reviews.ReviewTarget("movie", "tmdb", "1")

        active = public_reviews.collect_reviews(
            target,
            user=None,
            providers=(public_reviews.ReviewProvider("empty", lambda *_: []),),
        )
        inactive = public_reviews.collect_reviews(target, user=None, providers=())

        self.assertTrue(active.any_provider_active)
        self.assertFalse(inactive.any_provider_active)

    def test_blank_provider_entries_are_not_rendered_as_reviews(self):
        target = public_reviews.ReviewTarget("movie", "tmdb", "1")

        feed = public_reviews.collect_reviews(
            target,
            user=None,
            providers=(
                public_reviews.ReviewProvider(
                    "TMDB",
                    lambda *_: [{"author": "Alice", "body": "   "}],
                ),
            ),
        )

        self.assertEqual([], feed.reviews)

    def test_providers_are_fetched_concurrently(self):
        barrier = Barrier(2)

        def fetch(*_args):
            barrier.wait(timeout=1)
            return [review("Ready")]

        feed = public_reviews.collect_reviews(
            public_reviews.ReviewTarget("movie", "tmdb", "1"),
            user=None,
            providers=(
                public_reviews.ReviewProvider("one", fetch),
                public_reviews.ReviewProvider("two", fetch),
            ),
        )

        self.assertEqual(2, len(feed.reviews))

    def test_feed_exposes_provider_counts_and_more_pages(self):
        provider_page = public_reviews.ProviderReviewPage(
            reviews=[review("Alice")],
            total=21,
            has_more=True,
        )

        feed = public_reviews.collect_reviews(
            public_reviews.ReviewTarget("movie", "tmdb", "1"),
            user=None,
            providers=(public_reviews.ReviewProvider("TMDB", lambda *_: provider_page),),
        )

        self.assertEqual({"TMDB": 21}, feed.provider_counts)
        self.assertEqual({"TMDB": True}, feed.provider_has_more)
        self.assertTrue(feed.has_more)


class TmdbPublicReviewTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(TMDB_API="tmdb-key", TMDB_LANG="en-US")
    @patch("app.providers.tmdb.services.api_request")
    def test_movie_reviews_are_normalized_and_length_bounded(self, api_request):
        api_request.return_value = {
            "results": [
                {
                    "author": "Alice",
                    "content": "Excellent film.",
                    "created_at": "2026-08-01T12:30:00.000Z",
                    "url": "https://www.themoviedb.org/review/1",
                    "author_details": {"rating": 8.5},
                }
            ]
        }

        api_request.return_value["total_results"] = 21
        api_request.return_value["total_pages"] = 2

        result = tmdb.public_reviews("movie", "123", page=1, page_size=20, language="fr-FR")

        self.assertEqual("Alice", result.reviews[0]["author"])
        self.assertEqual(8.5, result.reviews[0]["score"])
        self.assertEqual(21, result.total)
        self.assertTrue(result.has_more)
        api_request.assert_called_once()
        self.assertIn("/movie/123/reviews", api_request.call_args.args[2])
        self.assertEqual("fr-FR", api_request.call_args.kwargs["params"]["language"])
        self.assertEqual(1, api_request.call_args.kwargs["params"]["page"])

        cached = tmdb.public_reviews("movie", "123", page=1, page_size=20, language="fr-FR")

        self.assertEqual(result, cached)
        api_request.assert_called_once()

    @override_settings(TMDB_API="tmdb-key", BETASERIES_API_KEY="")
    @patch("app.providers.tmdb.public_reviews")
    def test_provider_uses_the_authenticated_users_metadata_language(self, fetch):
        target = public_reviews.ReviewTarget("movie", "tmdb", "123")
        user = SimpleNamespace(is_authenticated=True, metadata_language="de-DE")

        provider = public_reviews.providers_for_target(target, user)[0]
        provider.fetch(target, user, 2, 20)

        fetch.assert_called_once_with("movie", "123", page=2, page_size=20, language="de-DE")


class BetaSeriesPublicReviewTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(BETASERIES_API_KEY="beta-key")
    @patch("app.providers.betaseries.services.api_request")
    def test_episode_resolution_and_reviews_are_cached_together(self, api_request):
        api_request.side_effect = [
            {"show": {"id": 1161, "resource_url": "https://www.betaseries.com/serie/lost"}, "errors": []},
            {"episodes": [{"id": 9981}], "errors": []},
            {"comments": [{"login": "Alice", "text": "A revealing episode.", "in_reply_to": 0}], "errors": []},
        ]
        target = public_reviews.ReviewTarget(
            "episode",
            "tvdb",
            "73739",
            external_ids={"tvdb_id": "73739"},
            season_number=1,
            episode_number=2,
        )

        first = betaseries.public_reviews(target)
        second = betaseries.public_reviews(target)

        self.assertEqual(first, second)
        self.assertEqual(3, api_request.call_count)

    @override_settings(BETASERIES_API_KEY="beta-key")
    @patch("app.providers.betaseries.services.api_request")
    def test_root_comments_use_real_response_fields_and_double_user_note(self, api_request):
        api_request.side_effect = [
            {"movie": {"id": 8342, "resource_url": "https://www.betaseries.com/film/matrix"}, "errors": []},
            {
                "comments": [
                    {"id": 1, "login": "Alice", "date": "2026-08-02 10:00:00", "text": "Great.", "user_note": 4, "in_reply_to": 0},
                    {"id": 2, "login": "Bob", "date": "2026-08-02 11:00:00", "text": "Reply", "user_note": 5, "in_reply_to": 1},
                ],
                "errors": [],
            },
        ]

        result = betaseries.public_reviews(
            public_reviews.ReviewTarget("movie", "tmdb", "603"),
            user=None,
            page=1,
            page_size=20,
        )

        self.assertEqual(1, len(result.reviews))
        self.assertEqual(8, result.reviews[0]["score"])
        self.assertEqual("https://www.betaseries.com/film/matrix", result.reviews[0]["url"])
        self.assertEqual(20, api_request.call_args.kwargs["params"]["nbpp"])
        self.assertNotIn("start", api_request.call_args.kwargs["params"])

        betaseries.public_reviews(
            public_reviews.ReviewTarget("movie", "tmdb", "603"),
            user=None,
            page=1,
            page_size=20,
        )

        self.assertEqual(2, api_request.call_count)

        second_page = betaseries.public_reviews(
            public_reviews.ReviewTarget("movie", "tmdb", "603"),
            user=None,
            page=2,
            page_size=20,
        )

        self.assertEqual([], second_page.reviews)
        self.assertEqual(2, api_request.call_count)

    @override_settings(BETASERIES_API_KEY="beta-key")
    @patch("app.providers.betaseries.services.api_request")
    def test_api_error_is_reported_as_a_provider_failure(self, api_request):
        api_request.return_value = {"errors": [{"code": 400, "text": "Bad request"}]}

        with self.assertRaises(RuntimeError):
            betaseries.public_reviews(
                public_reviews.ReviewTarget("movie", "tmdb", "603"),
                user=None,
            )


class HardcoverPublicReviewTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(HARDCOVER_API="hardcover-key")
    @patch("app.providers.hardcover.services.api_request")
    def test_reviews_enforce_limit_and_reject_short_or_blank_bodies(self, api_request):
        api_request.return_value = {
            "data": {
                "books": [
                    {
                        "slug": "dune",
                        "user_books": [
                            {"review_raw": "Short", "rating": 5, "user": {"username": "skip"}},
                            {"review_raw": "A thoughtful review long enough.", "rating": 4.5, "created_at": "2026-08-03T10:00:00+00:00", "user": {"username": "reader", "name": "Alice"}},
                        ],
                        "user_books_aggregate": {"aggregate": {"count": 42}},
                    }
                ]
            }
        }

        result = hardcover.public_reviews("312460", user=None, page=2, page_size=20)

        self.assertEqual(["Alice"], [item["author"] for item in result.reviews])
        self.assertEqual(9, result.reviews[0]["score"])
        self.assertEqual(42, result.total)
        self.assertTrue(result.has_more)
        variables = api_request.call_args.kwargs["params"]["variables"]
        self.assertEqual(
            {"id": 312460, "limit": 20, "offset": 20, "min_length": 20},
            variables,
        )

        hardcover.public_reviews("312460", user=None, page=2, page_size=20)

        api_request.assert_called_once()
