"""Build local integration availability for private media detail pages."""

from collections import defaultdict
from datetime import timedelta
from urllib.parse import quote, urlencode

from django.conf import settings
from django.utils import timezone

from app.models import CollectionEntry, MediaTypes, Sources
from integrations.models import (
    CollectionSourceState,
    PlexAccount,
    RadarrInstance,
    SonarrInstance,
)


def _sync_status(instance) -> str:
    if instance.connection_broken:
        return "error"
    if instance.last_sync_at is None:
        return "pending"
    stale_after = timedelta(hours=settings.DETAIL_AVAILABILITY_STALE_HOURS)
    if instance.last_sync_at < timezone.now() - stale_after:
        return "stale"
    return "current"


def _manual_search_url(base_url: str, term: str) -> str:
    return f"{base_url.rstrip('/')}/add/new?{urlencode({'term': term})}"


def _season_counts(states) -> list[dict]:
    counts = defaultdict(int)
    for state in states:
        if state.item.season_number is not None:
            counts[state.item.season_number] += 1
    return [
        {"season_number": season_number, "available_episodes": count}
        for season_number, count in sorted(counts.items())
    ]


def _plex_availability(user, item, media_type: str, title: str) -> dict | None:
    try:
        account = user.plex_account
    except PlexAccount.DoesNotExist:
        return None
    if not account.is_connected:
        return None

    entry = (
        CollectionEntry.objects.filter(user=user, item=item)
        .exclude(plex_rating_key__isnull=True)
        .exclude(plex_rating_key="")
        .order_by("-updated_at", "-id")
        .first()
    )
    seasons = []
    if media_type in {
        MediaTypes.TV.value,
        MediaTypes.ANIME.value,
        MediaTypes.SEASON.value,
    }:
        episode_filter = {
            "item__media_id": item.media_id,
            "item__source": item.source,
            "item__media_type": MediaTypes.EPISODE.value,
        }
        if media_type == MediaTypes.SEASON.value:
            episode_filter["item__season_number"] = item.season_number
        episode_entries = (
            CollectionEntry.objects.filter(user=user, **episode_filter)
            .exclude(plex_rating_key__isnull=True)
            .exclude(plex_rating_key="")
            .select_related("item")
        )
        seasons = _season_counts(episode_entries)

    if entry and account.machine_identifier:
        rating_key = quote(str(entry.plex_rating_key), safe="")
        machine_id = quote(str(account.machine_identifier), safe="")
        return {
            "key": "plex",
            "label": "Plex",
            "status": "available",
            "seasons": seasons,
            "action_label": "Open in Plex",
            "url": (
                "https://app.plex.tv/desktop/#!/server/"
                f"{machine_id}/details?key=%2Flibrary%2Fmetadata%2F{rating_key}"
            ),
        }

    return {
        "key": "plex",
        "label": "Plex",
        "status": "available" if seasons else "not_found",
        "seasons": seasons,
        "action_label": "Search Plex",
        "url": (
            "https://app.plex.tv/desktop/#!/search?"
            f"{urlencode({'query': title}, quote_via=quote)}"
        ),
    }


def _radarr_availability(user, item) -> dict | None:
    instances = list(RadarrInstance.objects.filter(user=user).order_by("created_at", "id"))
    if not instances:
        return None

    states = {
        state.source_instance_id: state
        for state in CollectionSourceState.objects.filter(
            user=user,
            item=item,
            source="radarr",
            source_instance_id__isnull=False,
        )
    }
    external_ids = item.provider_external_ids or {}
    tmdb_id = (
        item.media_id
        if item.source == Sources.TMDB.value
        else external_ids.get("tmdb_id")
    )
    term = f"tmdb:{tmdb_id}" if tmdb_id else item.title
    rows = []
    for instance in instances:
        state = states.get(instance.id)
        rows.append(
            {
                "label": instance.display_name,
                "status": "available" if state else "not_found",
                "sync_status": _sync_status(instance),
                "detail": state.quality_label if state else "",
                "action_label": "Search Radarr",
                "url": _manual_search_url(instance.base_url, term),
            }
        )
    return {"key": "radarr", "label": "Radarr", "instances": rows}


def _sonarr_search_term(item) -> str:
    external_ids = item.provider_external_ids or {}
    tvdb_id = external_ids.get("tvdb_id")
    if item.source == Sources.TVDB.value:
        tvdb_id = item.media_id
    return f"tvdb:{tvdb_id}" if tvdb_id else item.title


def _sonarr_availability(user, item, media_type: str) -> dict | None:
    instances = list(SonarrInstance.objects.filter(user=user).order_by("created_at", "id"))
    if not instances:
        return None

    item_filter = {
        "item__media_id": item.media_id,
        "item__source": item.source,
        "item__media_type": MediaTypes.EPISODE.value,
    }
    if media_type in {MediaTypes.SEASON.value, MediaTypes.EPISODE.value}:
        item_filter["item__season_number"] = item.season_number
    if media_type == MediaTypes.EPISODE.value:
        item_filter["item__episode_number"] = item.episode_number

    states = CollectionSourceState.objects.filter(
        user=user,
        source="sonarr",
        source_instance_id__isnull=False,
        **item_filter,
    ).select_related("item")
    seasons_by_instance = defaultdict(list)
    for state in states:
        seasons_by_instance[state.source_instance_id].append(state)

    direct_state_instance_ids = set(
        CollectionSourceState.objects.filter(
            user=user,
            item=item,
            source="sonarr",
            source_instance_id__isnull=False,
        ).values_list("source_instance_id", flat=True)
    )

    term = _sonarr_search_term(item)
    rows = []
    for instance in instances:
        seasons = _season_counts(seasons_by_instance.get(instance.id, []))
        available = bool(seasons) or instance.id in direct_state_instance_ids
        rows.append(
            {
                "label": instance.display_name,
                "status": "available" if available else "not_found",
                "sync_status": _sync_status(instance),
                "detail": "",
                "seasons": seasons,
                "action_label": "Search Sonarr",
                "url": _manual_search_url(instance.base_url, term),
            }
        )
    return {"key": "sonarr", "label": "Sonarr", "instances": rows}


def build_detail_availability(*, user, item, media_type: str, title: str) -> dict | None:
    """Return private, template-ready availability using only persisted local state."""
    if not user.is_authenticated or not user.detail_availability_enabled:
        return None

    services = []
    if user.detail_availability_plex_enabled:
        plex = _plex_availability(user, item, media_type, title)
        if plex:
            services.append(plex)

    if (
        user.detail_availability_radarr_enabled
        and media_type == MediaTypes.MOVIE.value
    ):
        radarr = _radarr_availability(user, item)
        if radarr:
            services.append(radarr)

    if user.detail_availability_sonarr_enabled and media_type in {
        MediaTypes.TV.value,
        MediaTypes.ANIME.value,
        MediaTypes.SEASON.value,
        MediaTypes.EPISODE.value,
    }:
        sonarr = _sonarr_availability(user, item, media_type)
        if sonarr:
            services.append(sonarr)

    return {"services": services}
