from datetime import UTC, datetime

from django.test import SimpleTestCase

from app.history_entry_builders import _group_consecutive_episode_entries
from app.models import MediaTypes


def _episode_entry(number, *, season=1, show_id="show-1", minutes=24):
    return {
        "media_type": MediaTypes.EPISODE.value,
        "item": {
            "media_id": show_id,
            "source": "manual",
            "season_number": season,
            "episode_number": number,
            "title": f"Episode {number}",
        },
        "show": {"title": "Example Show"},
        "title": f"Episode {number}",
        "display_title": f"Episode {number}",
        "episode_label": f"{season}x{number:02d}",
        "episode_code": f"S{season:02d}E{number:02d}",
        "season_number": season,
        "episode_number": number,
        "played_at_local": datetime(2026, 8, 24, number, tzinfo=UTC),
        "runtime_minutes": minutes,
        "runtime_display": f"{minutes}min",
        "instance_id": number,
        "entry_key": str(number),
    }


class ConsecutiveEpisodeGroupingTests(SimpleTestCase):
    def test_groups_adjacent_descending_episodes_from_the_same_season(self):
        grouped = _group_consecutive_episode_entries(
            [_episode_entry(3), _episode_entry(2), _episode_entry(1)]
        )

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["group_title"], "Example Show")
        self.assertEqual(grouped[0]["episode_label"], "1x01-03")
        self.assertEqual(grouped[0]["episode_code"], "S01E01-E03")
        self.assertEqual(grouped[0]["runtime_minutes"], 72)
        self.assertEqual(grouped[0]["runtime_display"], "1h 12min")
        self.assertEqual(grouped[0]["group_count"], 3)
        self.assertTrue(grouped[0]["is_episode_group"])

    def test_unrelated_activity_breaks_an_episode_run(self):
        movie = {
            "media_type": MediaTypes.MOVIE.value,
            "title": "Intermission",
            "entry_key": "movie-1",
        }

        entries = [_episode_entry(3), movie, _episode_entry(2)]

        self.assertEqual(_group_consecutive_episode_entries(entries), entries)

    def test_duplicate_episode_and_new_season_remain_separate(self):
        entries = [
            _episode_entry(2),
            _episode_entry(2),
            _episode_entry(1, season=2),
        ]

        self.assertEqual(_group_consecutive_episode_entries(entries), entries)
