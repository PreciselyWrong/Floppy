"""Reconcile upstream data repairs on the deployed fork migration graph.

Canonical tag merging and removal of proven stale deletion markers cannot be
undone automatically. Restore the pre-upgrade backup for their original form.
"""

from django.db import migrations
from django.db.models import Exists, OuterRef


TRACKED_MODELS = {
    "tv": "TV", "anime": "Anime", "movie": "Movie", "manga": "Manga",
    "book": "Book", "comic": "Comic", "game": "Game", "boardgame": "BoardGame",
    "music": "Music", "podcast": "Podcast",
}


def normalize_tag_names(apps, schema_editor):
    """Merge canonical names within each owner, retaining every item link."""
    alias = schema_editor.connection.alias
    tags = apps.get_model("app", "Tag").objects.using(alias)
    links = apps.get_model("app", "ItemTag").objects.using(alias)
    for tag in tags.order_by("pk").iterator(chunk_size=500):
        canonical = " ".join(tag.name.split())
        if canonical == tag.name:
            continue
        keeper = tags.filter(user_id=tag.user_id, name__iexact=canonical).exclude(pk=tag.pk).order_by("pk").first()
        if keeper is None:
            tags.filter(pk=tag.pk).update(name=canonical)
            continue
        existing_items = links.filter(tag_id=keeper.pk).values("item_id")
        links.filter(tag_id=tag.pk).exclude(item_id__in=existing_items).update(tag_id=keeper.pk)
        tags.filter(pk=tag.pk).delete()


def clear_stale_tombstones(apps, schema_editor):
    """Remove only markers contradicted by the same owner's tracked identity."""
    alias = schema_editor.connection.alias
    deleted = apps.get_model("app", "DeletedMedia").objects.using(alias)
    for media_type, model_name in TRACKED_MODELS.items():
        tracked = apps.get_model("app", model_name)._default_manager.using(alias).filter(
            user_id=OuterRef("user_id"), item__media_type=media_type,
            item__source=OuterRef("source"), item__media_id=OuterRef("media_id"),
        )
        stale = deleted.filter(media_type=media_type).filter(Exists(tracked))
        while ids := list(stale.values_list("pk", flat=True)[:1000]):
            deleted.filter(pk__in=ids).delete()


class Migration(migrations.Migration):
    dependencies = [("app", "0183_gameartwork")]
    operations = [
        migrations.RunPython(normalize_tag_names, migrations.RunPython.noop),
        migrations.RunPython(clear_stale_tombstones, migrations.RunPython.noop),
    ]
