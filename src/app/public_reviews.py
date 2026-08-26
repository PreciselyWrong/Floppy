from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime

from django.utils.dateparse import parse_datetime


@dataclass(frozen=True)
class ReviewTarget:
    """Provider-neutral identity for a media title or episode."""

    media_type: str
    source: str
    media_id: str
    external_ids: dict = field(default_factory=dict)
    season_number: int | None = None
    episode_number: int | None = None


@dataclass(frozen=True)
class PublicReview:
    """Normalized public review rendered by detail pages."""

    provider: str
    author: str
    body: str
    published_at: datetime | None = None
    score: float | None = None
    url: str | None = None
    provider_url: str = ""
    provider_logo: str = ""


@dataclass(frozen=True)
class ReviewProblem:
    """One isolated provider failure."""

    provider: str
    reason: str


@dataclass(frozen=True)
class ReviewFeed:
    """Combined reviews and provider outcomes."""

    reviews: list[PublicReview]
    problems: list[ReviewProblem]
    any_provider_active: bool
    provider_counts: dict[str, int] = field(default_factory=dict)
    has_more: bool = False
    provider_has_more: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderReviewPage:
    """One bounded provider page and its pagination metadata."""

    reviews: list
    total: int | None = None
    has_more: bool = False


@dataclass(frozen=True)
class ReviewProvider:
    """Configured provider fetch callback."""

    name: str
    fetch: Callable
    homepage: str = ""
    logo: str = ""


def _sort_key(review, attribute, *, descending):
    value = getattr(review, attribute)
    return (value is None, -value.timestamp() if descending and value else value)


def sort_reviews(reviews: Iterable[PublicReview], sort="recent"):
    """Sort reviews while keeping missing values at the end."""
    reviews = list(reviews)
    if sort == "oldest":
        return sorted(reviews, key=lambda review: _sort_key(review, "published_at", descending=False))
    if sort == "best":
        return sorted(reviews, key=lambda review: (review.score is None, -(review.score or 0)))
    if sort == "worst":
        return sorted(reviews, key=lambda review: (review.score is None, review.score or 0))
    return sorted(reviews, key=lambda review: _sort_key(review, "published_at", descending=True))


def _normalize(provider, value):
    published_at = value.get("published_at")
    if isinstance(published_at, str):
        published_at = parse_datetime(published_at)
    return PublicReview(
        provider=provider.name,
        author=(value.get("author") or "Anonymous").strip(),
        body=(value.get("body") or "").strip(),
        published_at=published_at,
        score=value.get("score"),
        url=value.get("url"),
        provider_url=provider.homepage,
        provider_logo=provider.logo,
    )


def collect_reviews(target, user, providers, *, page=1, page_size=20):
    """Fetch configured providers independently and combine their results."""
    providers = tuple(providers)

    def fetch_provider(provider):
        try:
            result = provider.fetch(target, user, page, page_size)
            provider_page = (
                result
                if isinstance(result, ProviderReviewPage)
                else ProviderReviewPage(list(result))
            )
            normalized = [
                replace(
                    value,
                    provider=value.provider or provider.name,
                    provider_url=value.provider_url or provider.homepage,
                    provider_logo=value.provider_logo or provider.logo,
                )
                if isinstance(value, PublicReview)
                else _normalize(provider, value)
                for value in provider_page.reviews
            ]
        except Exception as exc:  # Providers fail independently by design.
            return provider, [], None, ReviewProblem(
                provider.name,
                str(exc) or type(exc).__name__,
            )
        else:
            normalized = [review for review in normalized if review.body]
            return provider, normalized, provider_page, None

    if not providers:
        return ReviewFeed([], [], False)
    with ThreadPoolExecutor(max_workers=min(len(providers), 3)) as executor:
        outcomes = list(executor.map(fetch_provider, providers))

    reviews = []
    problems = []
    provider_counts = {}
    provider_has_more = {}
    has_more = False
    for provider, provider_reviews, provider_page, problem in outcomes:
        if problem:
            problems.append(problem)
            continue
        reviews.extend(provider_reviews)
        provider_counts[provider.name] = (
            provider_page.total
            if provider_page.total is not None
            else len(provider_reviews)
        )
        provider_has_more[provider.name] = provider_page.has_more
        has_more = has_more or provider_page.has_more
    return ReviewFeed(
        sort_reviews(reviews),
        problems,
        True,
        provider_counts,
        has_more,
        provider_has_more,
    )


def providers_for_target(target, user=None):
    """Return configured providers supporting the target's exact media scope."""
    from django.conf import settings

    from app.providers import betaseries, hardcover, tmdb
    from app.services.metadata_resolution import metadata_language_default

    providers = []
    if (
        settings.TMDB_API
        and target.source == "tmdb"
        and target.media_type in {"movie", "tv", "anime"}
    ):
        providers.append(
            ReviewProvider(
                "TMDB",
                lambda target, user, page, page_size: tmdb.public_reviews(
                    target.media_type,
                    target.media_id,
                    page=page,
                    page_size=page_size,
                    language=metadata_language_default(user),
                ),
                "https://www.themoviedb.org/",
                "img/tmdb-logo.png",
            )
        )
    if betaseries.is_configured(user) and target.media_type in {
        "movie",
        "tv",
        "anime",
        "episode",
    }:
        providers.append(
            ReviewProvider(
                "BetaSeries",
                betaseries.public_reviews,
                "https://www.betaseries.com/",
            )
        )
    if (
        target.source == "hardcover"
        and target.media_type == "book"
        and hardcover._authorization_header(user)
    ):
        providers.append(
            ReviewProvider(
                "Hardcover",
                lambda target, user, page, page_size: hardcover.public_reviews(
                    target.media_id,
                    user,
                    page=page,
                    page_size=page_size,
                ),
                "https://hardcover.app/",
                "img/hardcover-logo.png",
            )
        )
    return tuple(providers)
