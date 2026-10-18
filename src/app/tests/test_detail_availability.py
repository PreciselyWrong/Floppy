from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.detail_availability import build_detail_availability
from app.models import CollectionEntry, Item, MediaTypes, Sources
from integrations.models import (
    CollectionSourceState,
    PlexAccount,
    PlexLibraryItem,
    PlexLibrarySection,
    RadarrInstance,
    SonarrInstance,
)


class DetailAvailabilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="availability-user",
            password="password",
        )
        self.movie = Item.objects.create(
            media_id="238",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title="The Godfather",
        )

    def build(self, item=None, media_type=None):
        item = item or self.movie
        return build_detail_availability(
            user=self.user,
            item=item,
            media_type=media_type or item.media_type,
            title=item.title,
        )

    def test_plex_uses_token_free_direct_link_when_rating_key_is_known(self):
        PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
            machine_identifier="machine-1",
        )
        CollectionEntry.objects.create(
            user=self.user,
            item=self.movie,
            plex_rating_key="1234",
            plex_uri="http://plex.local:32400",
        )

        plex = self.build()["services"][0]

        self.assertEqual(plex["key"], "plex")
        self.assertEqual(plex["status"], "available")
        self.assertEqual(plex["action_label"], "Open in Plex")
        self.assertEqual(
            plex["url"],
            "https://app.plex.tv/desktop/#!/server/machine-1/details?key=%2Flibrary%2Fmetadata%2F1234",
        )
        self.assertNotIn("encrypted-secret", plex["url"])

    def test_plex_falls_back_to_manual_title_search(self):
        PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
            machine_identifier="machine-1",
        )

        plex = self.build()["services"][0]

        self.assertEqual(plex["status"], "unknown")
        self.assertEqual(plex["action_label"], "Search Plex")
        self.assertIn("query=The%20Godfather", plex["url"])

    def test_plex_finds_untracked_tmdb_movie_in_fresh_library_index(self):
        account = PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
        )
        section = PlexLibrarySection.objects.create(
            account=account,
            machine_identifier="5900941bbd24ca259470e3fca3cb650eff39b0fe",
            section_id="1",
            title="Movies",
            media_type="movie",
            plex_uri="http://plex.local:32400",
            sync_status=PlexLibrarySection.SyncStatus.COMPLETE,
            last_synced_at=timezone.now(),
        )
        PlexLibraryItem.objects.create(
            section=section,
            rating_key="18264",
            media_type="movie",
            title="Ferrari",
            tmdb_id=self.movie.media_id,
        )

        plex = self.build()["services"][0]

        self.assertEqual(plex["status"], "available")
        self.assertEqual(plex["action_label"], "Open in Plex")
        self.assertIn("server/5900941bbd24ca259470e3fca3cb650eff39b0fe", plex["url"])
        self.assertIn("metadata%2F18264", plex["url"])

    def test_plex_reports_unknown_before_a_complete_library_index(self):
        PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
        )

        plex = self.build()["services"][0]

        self.assertEqual(plex["status"], "unknown")
        self.assertEqual(plex["sync_status"], "pending")

    @override_settings(PLEX_LIBRARY_INDEX_STALE_HOURS=24)
    def test_plex_only_reports_not_found_from_a_fresh_complete_index(self):
        account = PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
        )
        section = PlexLibrarySection.objects.create(
            account=account,
            machine_identifier="machine-1",
            section_id="1",
            title="Movies",
            media_type="movie",
            sync_status=PlexLibrarySection.SyncStatus.COMPLETE,
            last_synced_at=timezone.now(),
        )

        plex = self.build()["services"][0]
        self.assertEqual(plex["status"], "not_found")
        self.assertEqual(plex["sync_status"], "current")

        section.last_synced_at = timezone.now() - timedelta(days=2)
        section.save(update_fields=["last_synced_at"])
        plex = self.build()["services"][0]
        self.assertEqual(plex["status"], "unknown")
        self.assertEqual(plex["sync_status"], "stale")

    def test_plex_does_not_claim_absence_while_an_expected_library_is_unindexed(self):
        account = PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
            sections=[
                {"id": "1", "type": "movie", "machine_identifier": "machine-1"},
                {"id": "2", "type": "movie", "machine_identifier": "machine-1"},
            ],
        )
        PlexLibrarySection.objects.create(
            account=account,
            machine_identifier="machine-1",
            section_id="1",
            media_type="movie",
            sync_status=PlexLibrarySection.SyncStatus.COMPLETE,
            last_synced_at=timezone.now(),
        )

        plex = self.build()["services"][0]

        self.assertEqual(plex["status"], "unknown")
        self.assertEqual(plex["sync_status"], "pending")

    def test_plex_reports_episode_presence_by_season(self):
        show = Item.objects.create(
            media_id="1668",
            source=Sources.TMDB.value,
            media_type=MediaTypes.TV.value,
            title="Friends",
        )
        PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
            machine_identifier="machine-1",
        )
        for season_number, episode_number in ((1, 1), (1, 2), (3, 1)):
            episode = Item.objects.create(
                media_id=show.media_id,
                source=show.source,
                media_type=MediaTypes.EPISODE.value,
                title=f"Episode {episode_number}",
                season_number=season_number,
                episode_number=episode_number,
            )
            CollectionEntry.objects.create(
                user=self.user,
                item=episode,
                plex_rating_key=f"plex-{season_number}-{episode_number}",
            )

        plex = self.build(show, MediaTypes.TV.value)["services"][0]

        self.assertEqual(plex["status"], "available")
        self.assertEqual(
            plex["seasons"],
            [
                {"season_number": 1, "available_episodes": 2},
                {"season_number": 3, "available_episodes": 1},
            ],
        )

    @patch("requests.get")
    def test_builder_never_calls_an_integration_over_the_network(self, mock_get):
        PlexAccount.objects.create(
            user=self.user,
            plex_token="encrypted-secret",
            plex_username="nico",
        )
        RadarrInstance.objects.create(
            user=self.user,
            base_url="https://radarr.local",
            api_key="encrypted-key",
        )

        self.build()

        mock_get.assert_not_called()

    @override_settings(DETAIL_AVAILABILITY_STALE_HOURS=24)
    def test_radarr_reports_each_instance_without_hiding_partial_failures(self):
        available = RadarrInstance.objects.create(
            user=self.user,
            name="Movies",
            base_url="https://radarr.local/radarr",
            api_key="encrypted-key",
            last_sync_at=timezone.now(),
        )
        RadarrInstance.objects.create(
            user=self.user,
            name="4K",
            base_url="https://radarr-4k.local",
            api_key="encrypted-key",
            connection_broken=True,
            last_error_message="timeout",
        )
        RadarrInstance.objects.create(
            user=self.user,
            name="Archive",
            base_url="https://radarr-archive.local",
            api_key="encrypted-key",
            last_sync_at=timezone.now() - timedelta(days=2),
        )
        CollectionSourceState.objects.create(
            user=self.user,
            item=self.movie,
            source="radarr",
            source_instance_id=available.id,
            quality_label="2160p",
        )

        radarr = next(
            service for service in self.build()["services"] if service["key"] == "radarr"
        )
        rows = {row["label"]: row for row in radarr["instances"]}

        self.assertEqual(rows["Movies"]["status"], "available")
        self.assertEqual(rows["Movies"]["detail"], "2160p")
        self.assertEqual(rows["4K"]["sync_status"], "error")
        self.assertEqual(rows["Archive"]["sync_status"], "stale")
        self.assertIn("/add/new?term=tmdb%3A238", rows["4K"]["url"])
        self.assertNotIn("encrypted-key", str(radarr))

    def test_sonarr_aggregates_available_episodes_by_season(self):
        show = Item.objects.create(
            media_id="95396",
            source=Sources.TMDB.value,
            media_type=MediaTypes.TV.value,
            title="Severance",
            provider_external_ids={"tvdb_id": "371980"},
        )
        instance = SonarrInstance.objects.create(
            user=self.user,
            name="TV",
            base_url="https://sonarr.local",
            api_key="encrypted-key",
            last_sync_at=timezone.now(),
        )
        for season_number, episode_number in ((1, 1), (1, 2), (2, 1)):
            episode = Item.objects.create(
                media_id=show.media_id,
                source=show.source,
                media_type=MediaTypes.EPISODE.value,
                title=f"Episode {episode_number}",
                season_number=season_number,
                episode_number=episode_number,
            )
            CollectionSourceState.objects.create(
                user=self.user,
                item=episode,
                source="sonarr",
                source_instance_id=instance.id,
            )

        sonarr = next(
            service
            for service in self.build(show, MediaTypes.TV.value)["services"]
            if service["key"] == "sonarr"
        )

        self.assertEqual(sonarr["instances"][0]["status"], "available")
        self.assertEqual(
            sonarr["instances"][0]["seasons"],
            [
                {"season_number": 1, "available_episodes": 2},
                {"season_number": 2, "available_episodes": 1},
            ],
        )
        self.assertIn(
            "/add/new?term=tvdb%3A371980",
            sonarr["instances"][0]["url"],
        )

    def test_sonarr_reports_the_exact_episode_on_episode_details(self):
        episode = Item.objects.create(
            media_id="125988",
            source=Sources.TMDB.value,
            media_type=MediaTypes.EPISODE.value,
            title="The Getaway",
            season_number=3,
            episode_number=9,
        )
        other_episode = Item.objects.create(
            media_id=episode.media_id,
            source=episode.source,
            media_type=MediaTypes.EPISODE.value,
            title="Other Episode",
            season_number=3,
            episode_number=8,
        )
        instance = SonarrInstance.objects.create(
            user=self.user,
            name="TV",
            base_url="https://sonarr.local",
            api_key="encrypted-key",
            last_sync_at=timezone.now(),
        )
        CollectionSourceState.objects.create(
            user=self.user,
            item=other_episode,
            source="sonarr",
            source_instance_id=instance.id,
        )

        sonarr = next(
            service
            for service in self.build(episode)["services"]
            if service["key"] == "sonarr"
        )
        self.assertEqual(sonarr["instances"][0]["status"], "not_found")

        CollectionSourceState.objects.create(
            user=self.user,
            item=episode,
            source="sonarr",
            source_instance_id=instance.id,
        )

        sonarr = next(
            service
            for service in self.build(episode)["services"]
            if service["key"] == "sonarr"
        )
        self.assertEqual(sonarr["instances"][0]["status"], "available")
        self.assertEqual(
            sonarr["instances"][0]["seasons"],
            [{"season_number": 3, "available_episodes": 1}],
        )

    def test_disabled_section_and_provider_are_omitted(self):
        RadarrInstance.objects.create(
            user=self.user,
            base_url="https://radarr.local",
            api_key="encrypted-key",
        )
        self.user.detail_availability_radarr_enabled = False
        self.user.save(update_fields=["detail_availability_radarr_enabled"])

        self.assertEqual(self.build()["services"], [])

        self.user.detail_availability_enabled = False
        self.user.save(update_fields=["detail_availability_enabled"])
        self.assertIsNone(self.build())

    @patch("users.views.tmdb.metadata_languages", return_value=[("", "Server Default")])
    @patch("users.views.tmdb.watch_provider_regions", return_value=[("UNSET", "Not set")])
    def test_preferences_persist_section_and_provider_switches(
        self,
        _mock_regions,
        _mock_languages,
    ):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("preferences"),
            {
                "detail_availability_enabled": "1",
                "detail_availability_plex_enabled": "0",
                "detail_availability_radarr_enabled": "1",
                "detail_availability_sonarr_enabled": "0",
            },
        )

        self.assertRedirects(response, reverse("preferences"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.detail_availability_enabled)
        self.assertFalse(self.user.detail_availability_plex_enabled)
        self.assertTrue(self.user.detail_availability_radarr_enabled)
        self.assertFalse(self.user.detail_availability_sonarr_enabled)

        settings_response = self.client.get(reverse("preferences"))
        for field_name in (
            "detail_availability_enabled",
            "detail_availability_plex_enabled",
            "detail_availability_radarr_enabled",
            "detail_availability_sonarr_enabled",
        ):
            self.assertContains(settings_response, f'name="{field_name}"')
