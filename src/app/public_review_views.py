from urllib.parse import urlencode

from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from app import helpers
from app.models import Item
from app.public_reviews import (
    ReviewFeed,
    ReviewTarget,
    collect_reviews,
    providers_for_target,
    sort_reviews,
)
from users.appearance import detail_layout_family, detail_section_enabled

VALID_SORTS = {"recent", "oldest", "best", "worst"}
REVIEW_QUERY_KEYS = ("season", "episode", "tvdb_id", "imdb_id")
PAGE_SIZE = 20
MAX_PAGES = 10
SORT_LABELS = {
    "recent": "Most recent",
    "oldest": "Oldest",
    "best": "Highest rated",
    "worst": "Lowest rated",
}


def _target(media_type, source, media_id, request):
    item = Item.objects.filter(
        media_type=media_type,
        source=source,
        media_id=media_id,
    ).first()
    external_ids = dict(getattr(item, "provider_external_ids", None) or {})
    if source == "tvdb":
        external_ids.setdefault("tvdb_id", media_id)
    for key in ("tvdb_id", "imdb_id"):
        if value := request.GET.get(key):
            external_ids[key] = value
    return ReviewTarget(
        media_type=media_type,
        source=source,
        media_id=str(media_id),
        external_ids=external_ids,
        season_number=request.GET.get("season"),
        episode_number=request.GET.get("episode"),
    )


def _hidden(request, media_type):
    return not detail_section_enabled(
        request.user,
        detail_layout_family(media_type),
        "content",
        "reviews",
    )


def _review_querystring(request):
    return urlencode(
        {key: request.GET[key] for key in REVIEW_QUERY_KEYS if request.GET.get(key)}
    )


def _page_number(request):
    try:
        return min(max(int(request.GET.get("page", 1)), 1), MAX_PAGES)
    except (TypeError, ValueError):
        return 1


def _url(request, **updates):
    params = {
        key: request.GET[key]
        for key in (*REVIEW_QUERY_KEYS, "sort", "provider")
        if request.GET.get(key)
    }
    for key, value in updates.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    query = urlencode(params)
    return f"{request.path}?{query}" if query else request.path


def _collect_pages(target, user, providers, page):
    feeds = [
        collect_reviews(
            target,
            user,
            providers,
            page=page_number,
            page_size=PAGE_SIZE,
        )
        for page_number in range(1, page + 1)
    ]
    reviews = [review for feed in feeds for review in feed.reviews]
    problems = {
        problem.provider: problem
        for feed in feeds
        for problem in feed.problems
    }
    counts = {}
    for feed in feeds:
        for provider, count in feed.provider_counts.items():
            counts[provider] = max(counts.get(provider, 0), count)
    return ReviewFeed(
        reviews=reviews,
        problems=list(problems.values()),
        any_provider_active=bool(providers),
        provider_counts=counts,
        has_more=feeds[-1].has_more if feeds else False,
        provider_has_more=feeds[-1].provider_has_more if feeds else {},
    )


@login_not_required
@require_GET
def public_reviews_preview(request, source, media_type, media_id, title):
    """Render the two-review lazy detail-page preview."""
    if _hidden(request, media_type):
        return HttpResponse("")
    target = _target(media_type, source, media_id, request)
    providers = providers_for_target(target, request.user if request.user.is_authenticated else None)
    if not providers:
        return HttpResponse("")
    feed = collect_reviews(target, request.user, providers)
    review_querystring = _review_querystring(request)
    total_reviews = sum(feed.provider_counts.values()) or len(feed.reviews)
    return render(
        request,
        "app/components/public_reviews_preview.html",
        {
            "feed": feed,
            "reviews": feed.reviews[:2],
            "target": target,
            "title": title,
            "review_querystring": review_querystring,
            "retry_url": request.get_full_path(),
            "total_reviews": total_reviews,
        },
    )


@login_not_required
@require_GET
def public_reviews(request, source, media_type, media_id, title):
    """Render the complete sortable review feed."""
    if _hidden(request, media_type):
        return HttpResponse("")
    target = _target(media_type, source, media_id, request)
    providers = providers_for_target(target, request.user if request.user.is_authenticated else None)
    page = _page_number(request)
    feed = _collect_pages(target, request.user, providers, page)
    selected_sort = request.GET.get("sort", "recent")
    if selected_sort not in VALID_SORTS:
        selected_sort = "recent"
    selected_provider = request.GET.get("provider", "")
    provider_names = {provider.name for provider in providers}
    if selected_provider not in provider_names:
        selected_provider = ""
    reviews = feed.reviews
    if selected_provider:
        reviews = [review for review in reviews if review.provider == selected_provider]
    reviews = sort_reviews(reviews, selected_sort)
    provider_filters = [
        {
            "name": provider.name,
            "count": feed.provider_counts.get(provider.name, 0),
            "selected": selected_provider == provider.name,
            "url": _url(request, provider=provider.name, page=None),
        }
        for provider in providers
    ]
    can_load_more = (
        feed.provider_has_more.get(selected_provider, False)
        if selected_provider
        else feed.has_more
    )
    context = {
        "feed": feed,
        "reviews": reviews,
        "selected_sort": selected_sort,
        "selected_provider": selected_provider,
        "provider_filters": provider_filters,
        "all_provider_count": sum(feed.provider_counts.values()),
        "all_provider_url": _url(request, provider=None, page=None),
        "sort_options": [
            {
                "value": value,
                "label": label,
                "url": _url(request, sort=value, page=None),
            }
            for value, label in SORT_LABELS.items()
        ],
        "attributions": providers,
        "page": page,
        "next_page_url": _url(request, page=page + 1) if can_load_more else "",
        "retry_url": request.get_full_path(),
        "review_querystring": _review_querystring(request),
        "target": target,
        "title": title.replace("-", " ").title(),
    }
    template = (
        "app/components/public_reviews_content.html"
        if helpers.is_htmx_fragment(request)
        else "app/public_reviews.html"
    )
    return render(
        request,
        template,
        context,
    )
