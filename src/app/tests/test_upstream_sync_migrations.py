"""The fork migration graph must describe the upgraded runtime schema."""

import os
from unittest import skipIf

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TransactionTestCase, override_settings


@override_settings(MIGRATION_MODULES={})
class UpstreamSyncMigrationGraphTests(SimpleTestCase):
    def test_latest_state_contains_new_features_and_private_models(self):
        loader = MigrationLoader(None)
        apps = loader.project_state(loader.graph.leaf_nodes()).apps
        self.assertIsNotNone(apps.get_model("app", "GameArtwork"))
        self.assertIsNotNone(apps.get_model("app", "ApplicationSettings"))
        self.assertIsNotNone(apps.get_model("users", "HomePinnedItem"))
        self.assertIsNotNone(apps.get_model("integrations", "PlexLibraryItem"))
        self.assertIsNotNone(apps.get_model("integrations", "TMDbAccount"))
        self.assertIsNotNone(apps.get_model("integrations", "PlaytimeSnapshot"))
        delivery = apps.get_model("integrations", "OutboundStateDelivery")
        self.assertEqual(delivery._meta.get_field("operation").default, "watched")
        self.assertIsNotNone(
            apps.get_model("lists", "CustomListItem")._meta.get_field("rank")
        )


@skipIf(os.environ.get("FLOPPY_TEST_FAST_DB") == "1", "Requires real schema migrations")
class CustomUpgradePreservationTests(TransactionTestCase):
    def test_existing_fork_preferences_history_and_links_survive_upgrade(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = {
            "app": "0182_episodeorder_episodeorderchange_historicalvideo_and_more",
            "integrations": "0038_cataloggrant_embyaccount_externalreference_and_more",
            "lists": "0015_customlist_tiers_customlistitem_tier_and_more",
            "users": "0152_savedview_and_more",
        }
        before = [(app, previous.get(app, migration)) for app, migration in latest]
        try:
            executor.migrate(before)
            old = MigrationExecutor(connection).loader.project_state(before).apps
            user = old.get_model("users", "User").objects.create(
                username="existing-fork",
                logo_style="text",
                logo_text="NicoFlix",
                sidebar_history_enabled=False,
                home_stale_days_threshold=37,
            )
            other = old.get_model("users", "User").objects.create(username="other-fork")
            item = old.get_model("app", "Item").objects.create(
                source="tmdb",
                media_type="movie",
                media_id="550",
                title="Synthetic Movie",
            )
            movie = old.get_model("app", "Movie").objects.create(
                user_id=user.pk, item_id=item.pk, score=8
            )
            row = old.get_model("users", "HomeScreenRow").objects.create(
                user_id=user.pk,
                media_type="all",
                row_type="watch_history",
                filters={"binge_grouping": False, "media_types": ["movie"]},
                open_last_episode=False,
            )
            old.get_model("users", "HomePinnedItem").objects.create(
                user_id=user.pk, item_id=item.pk
            )
            branding = {
                "logo_text": "NicoFlix",
                "theme": "custom",
                "palette": {"accent": "#12abcd"},
            }
            old.get_model("app", "ApplicationSettings").objects.create(
                public_branding=branding
            )
            tags = old.get_model("app", "Tag")
            keeper = tags.objects.create(user_id=user.pk, name="Backlog")
            stray = tags.objects.create(user_id=user.pk, name=" Backlog ")
            foreign = tags.objects.create(user_id=other.pk, name="Backlog")
            old.get_model("app", "ItemTag").objects.create(
                tag_id=stray.pk, item_id=item.pk
            )
            stale = old.get_model("app", "DeletedMedia").objects.create(
                user_id=user.pk, media_type="movie", source="tmdb", media_id="550"
            )
            genuine = old.get_model("app", "DeletedMedia").objects.create(
                user_id=other.pk, media_type="movie", source="tmdb", media_id="550"
            )
            MigrationExecutor(connection).migrate(latest)
            upgraded = MigrationExecutor(connection).loader.project_state(latest).apps
            saved = upgraded.get_model("users", "User").objects.get(pk=user.pk)
            self.assertEqual(saved.logo_text, "NicoFlix")
            self.assertFalse(saved.sidebar_history_enabled)
            self.assertEqual(saved.home_stale_days_threshold, 37)
            saved_row = upgraded.get_model("users", "HomeScreenRow").objects.get(
                pk=row.pk
            )
            self.assertEqual(
                saved_row.filters, {"binge_grouping": False, "media_types": ["movie"]}
            )
            self.assertFalse(saved_row.open_last_episode)
            self.assertTrue(
                upgraded.get_model("users", "HomePinnedItem")
                .objects.filter(user_id=user.pk, item_id=item.pk)
                .exists()
            )
            self.assertEqual(
                upgraded.get_model("app", "ApplicationSettings")
                .objects.get()
                .public_branding,
                branding,
            )
            self.assertEqual(
                upgraded.get_model("app", "Movie").objects.get(pk=movie.pk).score, 8
            )
            self.assertEqual(
                list(
                    upgraded.get_model("app", "ItemTag").objects.values_list(
                        "tag_id", "item_id"
                    )
                ),
                [(keeper.pk, item.pk)],
            )
            self.assertTrue(
                upgraded.get_model("app", "Tag").objects.filter(pk=foreign.pk).exists()
            )
            self.assertFalse(
                upgraded.get_model("app", "DeletedMedia")
                .objects.filter(pk=stale.pk)
                .exists()
            )
            self.assertTrue(
                upgraded.get_model("app", "DeletedMedia")
                .objects.filter(pk=genuine.pk)
                .exists()
            )
        finally:
            MigrationExecutor(connection).migrate(latest)
