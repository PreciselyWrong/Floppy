import contextlib
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache

from app.providers import services
from app.public_reviews import ProviderReviewPage

BASE_URL = "https://api.betaseries.com"
REVIEW_LIMIT = 20
PUBLIC_REVIEWS_CACHE_TIMEOUT = 60 * 30


class BetaSeriesAPIError(RuntimeError):
    """BetaSeries returned a structured API error."""


def _headers(_user=None):
    key = settings.BETASERIES_API_KEY
    return {"X-BetaSeries-Key": key, "X-BetaSeries-Version": "3.3"} if key else {}


def is_configured(user=None):
    """Return whether a BetaSeries application key is available."""
    return bool(_headers(user))


def _get(path, params, user=None):
    payload = services.api_request(
        "betaseries",
        "GET",
        f"{BASE_URL}/{path}",
        params=params,
        headers=_headers(user),
    )
    if payload.get("errors"):
        raise BetaSeriesAPIError
    return payload


def _resolve_ref(target, user=None):
    cache_key = f"betaseries_ref_{target.media_type}_{target.source}_{target.media_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    external_ids = target.external_ids or {}
    if target.media_type == "movie":
        params = {"tmdb_id": target.media_id} if target.source == "tmdb" else {}
        if not params and external_ids.get("imdb_id"):
            params = {"imdb_id": external_ids["imdb_id"]}
        payload = _get("movies/movie", params, user)
        entry = payload.get("movie")
        catalogue = "movie"
    elif target.media_type in {"tv", "anime", "episode"}:
        tvdb_id = external_ids.get("tvdb_id") or (
            target.media_id if target.source == "tvdb" else None
        )
        imdb_id = external_ids.get("imdb_id")
        params = {"thetvdb_id": tvdb_id} if tvdb_id else {"imdb_id": imdb_id} if imdb_id else {}
        if not params:
            return None
        payload = _get("shows/display", params, user)
        entry = payload.get("show")
        catalogue = "show"
    else:
        return None

    if not entry:
        return None
    result = {"id": entry.get("id"), "type": catalogue, "url": entry.get("resource_url")}
    cache.set(cache_key, result)
    return result


def _resolve_episode_id(target, show_id, user=None):
    if target.season_number is None or target.episode_number is None:
        return None
    cache_key = (
        f"betaseries_episode_ref_{show_id}_"
        f"{target.season_number}_{target.episode_number}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    payload = _get(
        "shows/episodes",
        {
            "id": show_id,
            "season": target.season_number,
            "episode": target.episode_number,
        },
        user,
    )
    episode = next(iter(payload.get("episodes") or []), None)
    episode_id = episode.get("id") if episode else None
    if episode_id is not None:
        cache.set(cache_key, episode_id, PUBLIC_REVIEWS_CACHE_TIMEOUT)
    return episode_id


def public_reviews(target, user=None, page=1, page_size=REVIEW_LIMIT):
    """Return root public comments for a supported BetaSeries target."""
    if int(page) > 1:
        return ProviderReviewPage([])
    if not is_configured(user):
        return ProviderReviewPage([])
    ref = _resolve_ref(target, user)
    if not ref or not ref.get("id"):
        return ProviderReviewPage([])

    commented_id = ref["id"]
    comment_type = ref["type"]
    if target.media_type == "episode":
        commented_id = _resolve_episode_id(target, ref["id"], user)
        if commented_id is None:
            return ProviderReviewPage([])
        comment_type = "episode"

    page_size = max(1, min(int(page_size), REVIEW_LIMIT))
    cache_key = f"betaseries_public_reviews_v2_{comment_type}_{commented_id}_{page_size}"
    cached = cache.get(cache_key)
    if cached is not None:
        return ProviderReviewPage(**cached)
    payload = _get(
        "comments/comments",
        {
            "type": comment_type,
            "id": commented_id,
            "nbpp": page_size,
        },
        user,
    )
    reviews = []
    for comment in payload.get("comments") or []:
        if comment.get("in_reply_to", comment.get("inReplyTo", 0)) != 0:
            continue
        published_at = None
        with contextlib.suppress(TypeError, ValueError):
            published_at = datetime.strptime(
                f"{comment.get('date', '')}+0000",
                "%Y-%m-%d %H:%M:%S%z",
            ).astimezone(UTC)
        reviews.append(
            {
                "author": comment.get("login") or "Anonymous",
                "body": comment.get("text") or "",
                "score": comment.get("user_note") * 2 if comment.get("user_note") is not None else None,
                "published_at": published_at,
                "url": ref.get("url"),
            }
        )
    total = payload.get("total") or payload.get("total_comments")
    total = int(total) if total is not None else None
    result = {
        "reviews": reviews,
        "total": total,
        "has_more": False,
    }
    cache.set(cache_key, result, PUBLIC_REVIEWS_CACHE_TIMEOUT)
    return ProviderReviewPage(**result)
