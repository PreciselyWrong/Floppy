from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django_celery_beat.models import PeriodicTask

from integrations import plex as plex_api
from integrations.models import PlexAccount, PlexLibraryItem, PlexLibrarySection
from integrations.tasks import refresh_plex_library_index
from integrations.views import _ensure_plex_library_index_schedule


class PlexLibraryIndexClientTests(TestCase):
    @patch("integrations.plex.requests.get")
    def test_library_scan_requests_guids_and_exact_item_type(self, mock_get):
        response = Mock()
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = {
            "MediaContainer": {"Metadata": [], "totalSize": 0}
        }
        mock_get.return_value = response

        plex_api.fetch_section_all_items(
            "secret",
            "http://plex.local:32400",
            "2",
            item_type=4,
        )

        self.assertEqual(
            mock_get.call_args.kwargs["params"]["includeGuids"],
            1,
        )
        self.assertEqual(mock_get.call_args.kwargs["params"]["type"], 4)


class PlexLibraryIndexTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="plex-index")
        self.account = PlexAccount.objects.create(
            user=self.user,
            plex_token="secret",
            plex_username="nico",
            sections=[
                {
                    "id": "1",
                    "title": "Movies",
                    "type": "movie",
                    "machine_identifier": "machine-1",
                }
            ],
        )
        sections_patcher = patch(
            "integrations.tasks._plex_library_index.plex_api.list_sections",
            side_effect=lambda _token: self.account.sections,
        )
        sections_patcher.start()
        self.addCleanup(sections_patcher.stop)

    def test_connected_account_gets_recurring_library_index_schedule(self):
        _ensure_plex_library_index_schedule(self.user, self.account)

        task = PeriodicTask.objects.get(task="Refresh Plex library index")
        self.assertEqual(task.interval.every, 6)
        self.assertEqual(task.interval.period, "hours")
        self.assertIn(f'"user_id": {self.user.id}', task.kwargs)

    @patch("integrations.tasks._plex_library_index.plex_api.fetch_section_all_items")
    @patch("integrations.tasks._plex_library_index.plex_api.list_resources")
    def test_complete_scan_indexes_untracked_movie_and_prunes_removed_items(
        self,
        mock_resources,
        mock_fetch,
    ):
        section = PlexLibrarySection.objects.create(
            account=self.account,
            machine_identifier="machine-1",
            section_id="1",
            title="Movies",
            media_type="movie",
            plex_uri="http://plex.local:32400",
        )
        PlexLibraryItem.objects.create(
            section=section,
            rating_key="removed",
            media_type="movie",
            title="Removed",
            tmdb_id="1",
        )
        mock_resources.return_value = [
            {
                "machine_identifier": "machine-1",
                "connections": [{"uri": "http://plex.local:32400"}],
            }
        ]
        mock_fetch.return_value = (
            [
                {
                    "ratingKey": "18264",
                    "title": "Ferrari",
                    "Guid": [{"id": "tmdb://365620"}],
                }
            ],
            1,
        )

        result = refresh_plex_library_index(self.user.id)

        self.assertEqual(result, {"indexed": 1, "errors": 0})
        indexed = PlexLibraryItem.objects.get(section=section)
        self.assertEqual(indexed.rating_key, "18264")
        self.assertEqual(indexed.tmdb_id, "365620")
        section.refresh_from_db()
        self.assertEqual(section.sync_status, PlexLibrarySection.SyncStatus.COMPLETE)
        self.assertIsNotNone(section.last_synced_at)

    @patch("integrations.tasks._plex_library_index.plex_api.fetch_section_all_items")
    @patch("integrations.tasks._plex_library_index.plex_api.list_resources")
    def test_failed_scan_preserves_previous_rows_and_marks_section_unreliable(
        self,
        mock_resources,
        mock_fetch,
    ):
        section = PlexLibrarySection.objects.create(
            account=self.account,
            machine_identifier="machine-1",
            section_id="1",
            title="Movies",
            media_type="movie",
            plex_uri="http://plex.local:32400",
            sync_status=PlexLibrarySection.SyncStatus.COMPLETE,
        )
        previous = PlexLibraryItem.objects.create(
            section=section,
            rating_key="18264",
            media_type="movie",
            title="Ferrari",
            tmdb_id="365620",
        )
        mock_resources.return_value = [
            {
                "machine_identifier": "machine-1",
                "connections": [{"uri": "http://plex.local:32400"}],
            }
        ]
        mock_fetch.side_effect = RuntimeError("temporary failure")

        result = refresh_plex_library_index(self.user.id)

        self.assertEqual(result, {"indexed": 0, "errors": 1})
        self.assertTrue(PlexLibraryItem.objects.filter(pk=previous.pk).exists())
        section.refresh_from_db()
        self.assertEqual(section.sync_status, PlexLibrarySection.SyncStatus.ERROR)

    @patch("integrations.tasks._plex_library_index.plex_api.fetch_section_all_items")
    @patch("integrations.tasks._plex_library_index.plex_api.list_resources")
    def test_show_scan_indexes_exact_episodes_with_the_show_external_id(
        self,
        mock_resources,
        mock_fetch,
    ):
        self.account.sections = [
            {
                "id": "2",
                "title": "TV",
                "type": "show",
                "machine_identifier": "machine-1",
            }
        ]
        self.account.save(update_fields=["sections"])
        mock_resources.return_value = [
            {
                "machine_identifier": "machine-1",
                "connections": [{"uri": "http://plex.local:32400"}],
            }
        ]

        def fetch_items(*_args, item_type=None, **_kwargs):
            if item_type == 4:
                return (
                    [
                        {
                            "ratingKey": "102",
                            "title": "The Getaway",
                            "grandparentRatingKey": "100",
                            "parentIndex": 3,
                            "index": 9,
                        }
                    ],
                    1,
                )
            return (
                [
                    {
                        "ratingKey": "100",
                        "title": "Silo",
                        "Guid": [{"id": "tmdb://125988"}],
                    }
                ],
                1,
            )

        mock_fetch.side_effect = fetch_items

        refresh_plex_library_index(self.user.id)

        episode = PlexLibraryItem.objects.get(media_type="episode")
        self.assertEqual(episode.tmdb_id, "125988")
        self.assertEqual(episode.season_number, 3)
        self.assertEqual(episode.episode_number, 9)
