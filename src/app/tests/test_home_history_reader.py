from unittest.mock import patch

from django.test import SimpleTestCase

from app import history_cache_reader
from app.models import MediaTypes


def _entry(key, media_type, *, library_media_type=None):
    entry = {"entry_key": key, "media_type": media_type}
    if library_media_type:
        entry["library_media_type"] = library_media_type
    return entry


class RecentHistoryEntryReaderTests(SimpleTestCase):
    @patch("app.history_cache_reader.get_cached_history_window")
    def test_returns_one_bounded_entry_window_and_has_more(self, cached_window):
        cached_window.return_value = (
            [
                {
                    "entries": [
                        _entry("movie-3", MediaTypes.MOVIE.value),
                        _entry("anime-1", MediaTypes.EPISODE.value, library_media_type=MediaTypes.ANIME.value),
                        _entry("movie-2", MediaTypes.MOVIE.value),
                        _entry("movie-1", MediaTypes.MOVIE.value),
                        _entry("movie-0", MediaTypes.MOVIE.value),
                    ]
                }
            ],
            1,
        )

        entries, has_more = history_cache_reader.get_recent_history_entries(
            self.user,
            MediaTypes.MOVIE.value,
            limit=2,
            offset=1,
        )

        self.assertEqual([entry["entry_key"] for entry in entries], ["movie-2", "movie-1"])
        self.assertTrue(has_more)
        cached_window.assert_called_once()

    @patch("app.history_cache_reader.get_cached_history_window")
    def test_tv_and_anime_episode_history_remain_separate(self, cached_window):
        cached_window.return_value = (
            [
                {
                    "entries": [
                        _entry("tv", MediaTypes.EPISODE.value, library_media_type=MediaTypes.TV.value),
                        _entry("anime", MediaTypes.EPISODE.value, library_media_type=MediaTypes.ANIME.value),
                    ]
                }
            ],
            1,
        )

        entries, has_more = history_cache_reader.get_recent_history_entries(
            self.user,
            MediaTypes.ANIME.value,
            limit=14,
            offset=0,
        )

        self.assertEqual([entry["entry_key"] for entry in entries], ["anime"])
        self.assertFalse(has_more)

    @property
    def user(self):
        return object()
