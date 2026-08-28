"""Maintain a complete local Plex library index for read-only detail pages."""

import logging
import secrets

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from app.log_safety import exception_summary
from integrations import plex as plex_api
from integrations.models import PlexAccount, PlexLibraryItem, PlexLibrarySection
from integrations.plex import extract_external_ids_from_guids

logger = logging.getLogger(__name__)

PLEX_LIBRARY_INDEX_PAGE_SIZE = 500
PLEX_LIBRARY_INDEX_TASK_NAME = "Refresh Plex library index"


def _section_id(section: dict) -> str:
    value = section.get("id") or section.get("key") or ""
    value = str(value)
    return value.rsplit("/", 1)[-1]


def _section_uri(section: dict, resources: list[dict]) -> str:
    if section.get("uri"):
        return str(section["uri"])
    machine_id = section.get("machine_identifier")
    for resource in resources:
        if resource.get("machine_identifier") != machine_id:
            continue
        for connection in resource.get("connections", []):
            uri = connection.get("uri") if isinstance(connection, dict) else connection
            if uri:
                return str(uri)
    return ""


def _external_ids(entry: dict) -> dict[str, str]:
    guids = entry.get("Guid") or []
    if not guids and entry.get("guid"):
        guids = [{"id": entry["guid"]}]
    identifiers = extract_external_ids_from_guids(guids)
    return {
        "tmdb_id": str(identifiers.get("tmdb_id") or ""),
        "imdb_id": str(identifiers.get("imdb_id") or ""),
        "tvdb_id": str(identifiers.get("tvdb_id") or ""),
    }


def _optional_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _upsert_items(items: list[PlexLibraryItem]) -> None:
    if not items:
        return
    PlexLibraryItem.objects.bulk_create(
        items,
        update_conflicts=True,
        update_fields=[
            "media_type",
            "title",
            "tmdb_id",
            "imdb_id",
            "tvdb_id",
            "season_number",
            "episode_number",
            "scan_token",
            "updated_at",
        ],
        unique_fields=["section", "rating_key"],
    )


def _scan_pages(account, section, item_type=None):
    start = 0
    while True:
        entries, total = plex_api.fetch_section_all_items(
            account.plex_token,
            section.plex_uri,
            section.section_id,
            start=start,
            size=PLEX_LIBRARY_INDEX_PAGE_SIZE,
            item_type=item_type,
        )
        if not entries:
            break
        yield entries
        start += len(entries)
        if start >= total:
            break


def _scan_section(account, section) -> int:
    scan_token = secrets.token_hex(16)
    indexed = 0
    shows_by_rating_key = {}

    for entries in _scan_pages(account, section):
        batch = []
        for entry in entries:
            rating_key = str(entry.get("ratingKey") or entry.get("ratingkey") or "")
            if not rating_key:
                continue
            identifiers = _external_ids(entry)
            if section.media_type == "show":
                shows_by_rating_key[rating_key] = identifiers
            batch.append(
                PlexLibraryItem(
                    section=section,
                    rating_key=rating_key,
                    media_type=section.media_type,
                    title=str(entry.get("title") or ""),
                    scan_token=scan_token,
                    **identifiers,
                )
            )
        _upsert_items(batch)
        indexed += len(batch)

    if section.media_type == "show":
        for entries in _scan_pages(account, section, item_type=4):
            batch = []
            for entry in entries:
                rating_key = str(
                    entry.get("ratingKey") or entry.get("ratingkey") or ""
                )
                show_rating_key = str(entry.get("grandparentRatingKey") or "")
                identifiers = shows_by_rating_key.get(show_rating_key)
                if not rating_key or not identifiers or not any(identifiers.values()):
                    continue
                batch.append(
                    PlexLibraryItem(
                        section=section,
                        rating_key=rating_key,
                        media_type="episode",
                        title=str(entry.get("title") or ""),
                        season_number=_optional_positive_int(entry.get("parentIndex")),
                        episode_number=_optional_positive_int(entry.get("index")),
                        scan_token=scan_token,
                        **identifiers,
                    )
                )
            _upsert_items(batch)
            indexed += len(batch)

    with transaction.atomic():
        section.items.exclude(scan_token=scan_token).delete()
        section.sync_status = PlexLibrarySection.SyncStatus.COMPLETE
        section.last_synced_at = timezone.now()
        section.last_error = ""
        section.save(
            update_fields=["sync_status", "last_synced_at", "last_error", "updated_at"]
        )
    return indexed


@shared_task(name=PLEX_LIBRARY_INDEX_TASK_NAME)
def refresh_plex_library_index(user_id):
    """Refresh every movie/show section for one connected Plex account."""
    try:
        account = PlexAccount.objects.get(user_id=user_id)
    except PlexAccount.DoesNotExist:
        return {"indexed": 0, "errors": 0}

    try:
        resources = plex_api.list_resources(account.plex_token)
        plex_sections = plex_api.list_sections(account.plex_token)
        account.sections = plex_sections
        account.sections_refreshed_at = timezone.now()
        account.save(update_fields=["sections", "sections_refreshed_at", "updated_at"])
    except Exception as exc:
        error = exception_summary(exc)
        account.library_sections.update(
            sync_status=PlexLibrarySection.SyncStatus.ERROR,
            last_error=error,
        )
        logger.warning(
            "Plex library index discovery failed user_id=%s error=%s",
            user_id,
            error,
        )
        return {"indexed": 0, "errors": 1}

    indexed = 0
    errors = 0
    discovered_sections = set()
    for plex_section in plex_sections:
        media_type = str(plex_section.get("type") or "").lower()
        if media_type not in {"movie", "show"}:
            continue
        machine_id = str(plex_section.get("machine_identifier") or "")
        section_id = _section_id(plex_section)
        plex_uri = _section_uri(plex_section, resources)
        if not machine_id or not section_id:
            errors += 1
            continue
        discovered_sections.add((machine_id, section_id))
        section, _ = PlexLibrarySection.objects.update_or_create(
            account=account,
            machine_identifier=machine_id,
            section_id=section_id,
            defaults={
                "title": str(plex_section.get("title") or ""),
                "media_type": media_type,
                "plex_uri": plex_uri,
            },
        )
        section.sync_status = PlexLibrarySection.SyncStatus.PENDING
        section.last_error = ""
        section.save(update_fields=["sync_status", "last_error", "updated_at"])
        if not plex_uri:
            errors += 1
            section.sync_status = PlexLibrarySection.SyncStatus.ERROR
            section.last_error = "No Plex connection URI"
            section.save(update_fields=["sync_status", "last_error", "updated_at"])
            continue
        try:
            indexed += _scan_section(account, section)
        except Exception as exc:
            errors += 1
            section.sync_status = PlexLibrarySection.SyncStatus.ERROR
            section.last_error = exception_summary(exc)
            section.save(update_fields=["sync_status", "last_error", "updated_at"])
            logger.warning(
                "Plex library section index failed user_id=%s section_id=%s error=%s",
                user_id,
                section_id,
                exception_summary(exc),
            )

    for existing_section in account.library_sections.all():
        identity = (
            existing_section.machine_identifier,
            existing_section.section_id,
        )
        if identity not in discovered_sections:
            existing_section.delete()

    return {"indexed": indexed, "errors": errors}


@shared_task(name="Refresh all Plex library indexes")
def refresh_all_plex_library_indexes():
    """Queue one bounded index refresh for every connected Plex account."""
    for user_id in PlexAccount.objects.values_list("user_id", flat=True).iterator():
        refresh_plex_library_index.delay(user_id)
