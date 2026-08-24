from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from app.detail_builders import (
    _build_aggregate_rating_context,
    _build_detail_link_sections,
    _build_imdb_rating_context,
    _build_mal_rating_context,
    _build_series_graph_data,
    enrich_episode_rows,
    enrich_season_cards,
)
from app.models import Item, ItemProviderLink, MediaTypes, Sources


class DetailEnrichmentTests(TestCase):
    def test_episode_enrichment_marks_only_aired_non_special_gaps(self):
        now = timezone.now()
        rows = enrich_episode_rows(
            [
                {"episode_number": 1, "air_date": now - timedelta(days=3), "history": [{"id": 1}], "title": "One"},
                {"episode_number": 2, "air_date": now - timedelta(days=2), "history": [], "title": "Two"},
                {"episode_number": 3, "air_date": now - timedelta(days=1), "history": [{"id": 3}], "title": "Three"},
                {"episode_number": 4, "air_date": now + timedelta(days=1), "history": [], "title": "Four"},
            ],
            season_number=1,
            now=now,
            obfuscate_titles=True,
        )
        self.assertTrue(rows[1]["is_skipped"])
        self.assertEqual(rows[1]["display_title"], "Episode 2")
        self.assertFalse(rows[3]["is_skipped"])

        specials = enrich_episode_rows(
            [{"episode_number": 1, "air_date": now - timedelta(days=1), "history": []}],
            season_number=0,
            now=now,
        )
        self.assertFalse(specials[0]["is_skipped"])

    def test_season_cards_mark_resume_and_future(self):
        now = timezone.now()
        rows = enrich_season_cards(
            [
                {"season_number": 1, "first_air_date": now - timedelta(days=1), "progress": 2, "max_progress": 8},
                {"season_number": 2, "first_air_date": now + timedelta(days=1), "progress": 0, "max_progress": 8},
            ],
            now=now,
        )
        self.assertTrue(rows[0]["is_resume"])
        self.assertTrue(rows[1]["is_upcoming"])


class SeriesGraphBuilderTests(TestCase):
    """Focused coverage for the episode graph layout builder."""

    def test_include_unrated_preserves_episode_slots(self):
        """Unrated episodes should keep their grid positions during polling."""
        Item.objects.create(
            media_id="show-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="Special 1",
            season_number=0,
            episode_number=1,
            trakt_rating=9.0,
            trakt_rating_count=50,
        )
        Item.objects.create(
            media_id="show-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="Episode 1",
            season_number=1,
            episode_number=1,
            trakt_rating=8.0,
            trakt_rating_count=100,
        )
        Item.objects.create(
            media_id="show-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="Episode 2",
            season_number=1,
            episode_number=2,
        )

        graph_data = _build_series_graph_data(
            Sources.TMDB.value,
            "show-1",
            use_trakt=True,
            include_unrated=True,
        )

        self.assertIsNotNone(graph_data)
        self.assertEqual([season["label"] for season in graph_data["seasons"]], ["S1"])
        self.assertEqual([row["ep"] for row in graph_data["episode_rows"]], [1, 2])
        self.assertEqual(graph_data["episode_rows"][0]["cells"][0]["score"], 8.0)
        self.assertIsNone(graph_data["episode_rows"][1]["cells"][0]["score"])

    def test_use_imdb_reads_imdb_rating_fields(self):
        Item.objects.create(
            media_id="show-2",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="Episode 1",
            season_number=1,
            episode_number=1,
            imdb_rating=9.1,
            imdb_rating_count=1234,
        )

        graph_data = _build_series_graph_data(
            Sources.TMDB.value,
            "show-2",
            use_imdb=True,
        )

        self.assertIsNotNone(graph_data)
        self.assertEqual(graph_data["episode_rows"][0]["cells"][0]["score"], 9.1)
        self.assertEqual(graph_data["episode_rows"][0]["cells"][0]["votes"], 1234)


class ImdbRatingContextTests(TestCase):
    """Focused coverage for the IMDb rating chip context builder."""

    def test_returns_none_without_rating_count(self):
        item = Item.objects.create(
            media_id="movie-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title="A Movie",
        )

        self.assertIsNone(_build_imdb_rating_context(item, MediaTypes.MOVIE.value))

    def test_returns_rounded_rating_and_count(self):
        item = Item.objects.create(
            media_id="movie-2",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title="Another Movie",
            imdb_rating=7.88,
            imdb_rating_count=54321,
        )

        context = _build_imdb_rating_context(item, MediaTypes.MOVIE.value)

        self.assertEqual(context, {"rating": 7.8, "rating_count": 54321})

    def test_returns_none_for_unsupported_media_type(self):
        item = Item.objects.create(
            media_id="season-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.SEASON.value,
            title="Season 1",
            season_number=1,
            imdb_rating=8.0,
            imdb_rating_count=100,
        )

        self.assertIsNone(_build_imdb_rating_context(item, MediaTypes.SEASON.value))


class MalRatingContextTests(TestCase):
    """Focused coverage for the MyAnimeList rating chip context."""

    def test_returns_truncated_one_decimal_rating_for_anime(self):
        item = Item.objects.create(
            media_id="52991",
            source=Sources.MAL.value,
            media_type=MediaTypes.ANIME.value,
            title="Frieren",
            mal_rating=8.78,
            mal_rating_count=1234,
        )

        self.assertEqual(
            _build_mal_rating_context(item, MediaTypes.ANIME.value),
            {"rating": 8.7, "rating_count": 1234},
        )

    def test_returns_none_without_rating_count_or_for_unsupported_media(self):
        unrated = Item.objects.create(
            media_id="52992",
            source=Sources.MAL.value,
            media_type=MediaTypes.ANIME.value,
            title="Unrated Anime",
            mal_rating=8.0,
        )
        missing_score = Item.objects.create(
            media_id="52993",
            source=Sources.MAL.value,
            media_type=MediaTypes.ANIME.value,
            title="Anime Without A Score",
            mal_rating_count=100,
        )
        manga = Item.objects.create(
            media_id="119735",
            source=Sources.MAL.value,
            media_type=MediaTypes.MANGA.value,
            title="Manga",
            mal_rating=8.0,
            mal_rating_count=100,
        )

        self.assertIsNone(
            _build_mal_rating_context(unrated, MediaTypes.ANIME.value)
        )
        self.assertIsNone(
            _build_mal_rating_context(missing_score, MediaTypes.ANIME.value)
        )
        self.assertIsNone(_build_mal_rating_context(manga, MediaTypes.MANGA.value))

    def test_supports_grouped_anime_using_the_tv_route(self):
        item = Item.objects.create(
            media_id="tv-1",
            source=Sources.TVDB.value,
            media_type=MediaTypes.TV.value,
            library_media_type=MediaTypes.ANIME.value,
            title="Grouped Anime",
            mal_rating=8.1,
            mal_rating_count=100,
        )

        self.assertEqual(
            _build_mal_rating_context(item, MediaTypes.TV.value),
            {"rating": 8.1, "rating_count": 100},
        )


class AggregateRatingContextTests(SimpleTestCase):
    def test_builds_weighted_rating_and_sorted_source_breakdown(self):
        item = SimpleNamespace(
            trakt_rating=6.0,
            imdb_rating=9.0,
            mal_rating=None,
        )

        context = _build_aggregate_rating_context(
            {
                "score": 8.0,
                "score_count": 100,
                "source_url": "https://www.themoviedb.org/movie/1",
                "external_links": {
                    "IMDb": "https://www.imdb.com/title/tt0000001/",
                },
            },
            item,
            Sources.TMDB.value,
            trakt_score={"rating": 6.0, "rating_count": 50},
            imdb_score={"rating": 9.0, "rating_count": 200},
        )

        self.assertEqual(context["rating"], 8.3)
        self.assertEqual(context["total_votes"], 350)
        self.assertEqual(context["source_count"], 3)
        self.assertEqual(
            [source["key"] for source in context["sources"]],
            ["imdb", "tmdb", "trakt"],
        )
        self.assertEqual(
            [source["weight"] for source in context["sources"]],
            [57.1, 28.6, 14.3],
        )
        self.assertEqual(
            context["sources"][0]["external_url"],
            "https://www.imdb.com/title/tt0000001/",
        )
        self.assertEqual(context["sources"][1]["label"], "The Movie Database")

    def test_excludes_invalid_scores_and_sources_without_votes(self):
        context = _build_aggregate_rating_context(
            {"score": 12, "score_count": 100},
            SimpleNamespace(
                trakt_rating=8.0,
                imdb_rating=None,
                mal_rating=None,
            ),
            Sources.TMDB.value,
            trakt_score={"rating": 8.0, "rating_count": 0},
        )

        self.assertIsNone(context)

    def test_deduplicates_primary_provider_and_uses_display_source_url(self):
        context = _build_aggregate_rating_context(
            {
                "score": 8.78,
                "score_count": 1234,
                "display_source_url": "https://myanimelist.net/anime/52991",
                "source_url": "https://example.test/fallback",
                "external_links": {
                    "MyAnimeList": "https://myanimelist.net/anime/52991",
                },
            },
            SimpleNamespace(
                trakt_rating=None,
                imdb_rating=None,
                mal_rating=8.78,
            ),
            Sources.MAL.value,
            mal_score={"rating": 8.7, "rating_count": 1234},
        )

        self.assertEqual(context["rating"], 8.8)
        self.assertEqual(context["source_count"], 1)
        self.assertEqual(context["sources"][0]["key"], Sources.MAL.value)
        self.assertEqual(
            context["sources"][0]["external_url"],
            "https://myanimelist.net/anime/52991",
        )


class DetailLinkSectionsMalTests(TestCase):
    def test_adds_exact_mal_link_for_flat_anime(self):
        item = Item.objects.create(
            media_id="52991",
            source=Sources.MAL.value,
            media_type=MediaTypes.ANIME.value,
            title="Frieren",
        )

        sections = _build_detail_link_sections(
            {
                "source_url": "https://www.themoviedb.org/tv/52991",
                "media_id": "52991",
            },
            MediaTypes.ANIME.value,
            Sources.TMDB.value,
            Sources.TMDB.value,
            item=item,
        )

        external_entries = sections[-1]["entries"]
        self.assertEqual(
            [(entry["label"], entry["url"]) for entry in external_entries],
            [("MyAnimeList", "https://myanimelist.net/anime/52991")],
        )

    def test_does_not_add_mal_link_for_ambiguous_grouped_anime(self):
        item = Item.objects.create(
            media_id="tv-1",
            source=Sources.TVDB.value,
            media_type=MediaTypes.TV.value,
            library_media_type=MediaTypes.ANIME.value,
            title="Ambiguous Anime",
            provider_external_ids={"mal_id": "3"},
        )
        ItemProviderLink.objects.create(
            item=item,
            provider=Sources.MAL.value,
            provider_media_type=MediaTypes.TV.value,
            provider_media_id="4",
        )

        sections = _build_detail_link_sections(
            {"source_url": "https://www.thetvdb.com/series/tv-1"},
            MediaTypes.ANIME.value,
            Sources.TVDB.value,
            Sources.TVDB.value,
            item=item,
        )

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["title"], "Source")
