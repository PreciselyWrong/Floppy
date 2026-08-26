"""Pure timeline transformations and binge grouping for History."""

from app import helpers
from app.models import MediaTypes

RUNTIME_UNKNOWN_AIRED = 999998
MIN_BINGE_SIZE = 2


def get_timeline_family(media_type: str | None) -> str:
    """Map a media_type to its timeline chip family: 'movies', 'series', 'books', or 'other'."""
    if not media_type:
        return "other"
    mt = str(media_type).strip().lower()
    if mt == MediaTypes.MOVIE.value:
        return "movies"
    if mt in (
        MediaTypes.TV.value,
        MediaTypes.SEASON.value,
        MediaTypes.EPISODE.value,
    ):
        return "series"
    if mt in (
        MediaTypes.BOOK.value,
        MediaTypes.COMIC.value,
        MediaTypes.MANGA.value,
    ):
        return "books"
    return "other"


def get_show_identity(entry: dict) -> tuple[str, str] | None:
    """Extract (source, media_id) identity for the series behind an episode entry."""
    if not isinstance(entry, dict):
        return None
    if entry.get("media_type") != MediaTypes.EPISODE.value:
        return None

    show = entry.get("show")
    if isinstance(show, dict):
        source = show.get("source")
        media_id = show.get("media_id")
        if source is not None and media_id is not None:
            return (str(source), str(media_id))
        if show.get("id") is not None:
            return ("id", str(show["id"]))
    elif show is not None:
        source = getattr(show, "source", None)
        media_id = getattr(show, "media_id", None)
        if source is not None and media_id is not None:
            return (str(source), str(media_id))
        show_id = getattr(show, "id", None)
        if show_id is not None:
            return ("id", str(show_id))

    return None


def format_episode_range(entries: list[dict]) -> str | None:
    """Format compact episode range only when all entries belong to a single season and all episode numbers exist."""
    if not entries:
        return None

    seasons = set()
    episodes = []
    for e in entries:
        if not isinstance(e, dict):
            return None
        s = e.get("season_number")
        ep = e.get("episode_number")
        if s is None or ep is None:
            return None
        try:
            seasons.add(int(s))
            episodes.append(int(ep))
        except (ValueError, TypeError):
            return None

    if len(seasons) != 1:
        return None

    season = seasons.pop()
    min_ep = min(episodes)
    max_ep = max(episodes)
    if min_ep == max_ep:
        return f"S{season:02d}E{min_ep:02d}"
    return f"S{season:02d}E{min_ep:02d}\N{EN DASH}E{max_ep:02d}"


def calculate_total_runtime(entries: list[dict]) -> tuple[int | None, str | None]:
    """Return (total_minutes, display_str) only when every entry has a known runtime."""
    if not entries:
        return None, None

    total_minutes = 0
    for e in entries:
        if not isinstance(e, dict):
            return None, None
        rt = e.get("runtime_minutes")
        if not rt or not isinstance(rt, int) or rt <= 0 or rt >= RUNTIME_UNKNOWN_AIRED:
            return None, None
        total_minutes += rt

    return total_minutes, helpers.minutes_to_hhmm(total_minutes)


def _build_binge_item(group_entries: list[dict]) -> dict:
    """Create a binge timeline group item from 2+ consecutive same-series episodes."""
    latest_entry = group_entries[0]
    show = latest_entry.get("show") or {}
    series_title = (
        (show.get("title") if isinstance(show, dict) else getattr(show, "title", None))
        or latest_entry.get("title")
        or "Series"
    )

    total_mins, total_display = calculate_total_runtime(group_entries)
    ep_range = format_episode_range(group_entries)

    return {
        "is_binge": True,
        "media_type": MediaTypes.EPISODE.value,
        "timeline_family": "series",
        "count": len(group_entries),
        "entries": group_entries,
        "first_entry": latest_entry,
        "show": show,
        "title": series_title,
        "display_title": series_title,
        "poster": latest_entry.get("poster"),
        "played_at_local": latest_entry.get("played_at_local"),
        "episode_range": ep_range,
        "runtime_minutes": total_mins,
        "runtime_display": total_display,
        "entry_key": f"binge-{latest_entry.get('entry_key')}-{len(group_entries)}",
    }


def _build_single_timeline_item(entry: dict) -> dict:
    """Wrap a single history entry in timeline item envelope."""
    media_type = entry.get("media_type") if isinstance(entry, dict) else None
    return {
        "is_binge": False,
        "media_type": media_type,
        "timeline_family": get_timeline_family(media_type),
        "entry": entry,
    }


def group_day_timeline_entries(entries: list[dict]) -> list[dict]:
    """Transform a day's raw history entries into timeline items with consecutive same-show binge grouping."""
    if not entries:
        return []

    timeline_items = []
    current_binge_entries = []
    current_show_id = None

    def flush_current():
        nonlocal current_binge_entries, current_show_id
        if not current_binge_entries:
            return
        if len(current_binge_entries) >= MIN_BINGE_SIZE:
            timeline_items.append(_build_binge_item(current_binge_entries))
        else:
            timeline_items.extend(
                _build_single_timeline_item(entry) for entry in current_binge_entries
            )
        current_binge_entries = []
        current_show_id = None

    for entry in entries:
        if not isinstance(entry, dict):
            flush_current()
            continue

        media_type = entry.get("media_type")
        if media_type == MediaTypes.EPISODE.value:
            show_id = get_show_identity(entry)
            if show_id and show_id == current_show_id:
                current_binge_entries.append(entry)
            else:
                flush_current()
                current_show_id = show_id
                current_binge_entries.append(entry)
        else:
            flush_current()
            timeline_items.append(_build_single_timeline_item(entry))

    flush_current()
    return timeline_items
