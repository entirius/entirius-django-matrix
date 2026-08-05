# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Search service — unified search (Phase 1: products + categories)."""

from django_matrix.models import Channel
from django_matrix.services.meta import build_meta
from django_matrix.services.product_service import count_products, list_products

# Shorter queries match most of the catalogue, so they are answered without touching the DB.
MIN_QUERY_LENGTH = 2


def search(
    channel: Channel,
    language,
    currency,
    country,
    query: str,
    scope: str = "products,categories",
    limit: int = 5,
    category: str | None = None,
    filters: dict | None = None,
    ranges: dict | None = None,
    sort: list[dict] | None = None,
    page: int = 1,
    page_size: int = 12,
    extra_warnings: list[dict] | None = None,
) -> dict:
    """Unified search. Returns sections based on scope param."""
    scopes = {s.strip() for s in scope.split(",")}
    result = {}
    warnings: list[dict] = list(extra_warnings or [])
    query = query.strip()

    if len(query) < MIN_QUERY_LENGTH:
        return _empty_result(scopes, warnings)

    if "products" in scopes:
        section, product_warnings = _search_products(
            sort,
            page,
            page_size,
            channel=channel,
            language=language,
            currency=currency,
            country=country,
            category=category,
            filters=filters,
            ranges=ranges,
            search=query,
        )
        result["products"] = section
        warnings = product_warnings + warnings

    if "categories" in scopes:
        result["categories"] = {"results": _search_categories(channel, language, query, limit)}

    result["phrases"] = _get_phrase_suggestions(channel, language, query, limit)
    result["meta"] = build_meta(warnings)

    return result


def _empty_result(scopes: set[str], warnings: list[dict]) -> dict:
    """Query below the minimum: the same scoped shape as a real response, nothing queried."""
    result = {}
    if "products" in scopes:
        result["products"] = {"total": 0, "results": [], "has_next_page": False}
    if "categories" in scopes:
        result["categories"] = {"results": []}
    result["phrases"] = []
    result["meta"] = build_meta(warnings)
    return result


def _search_products(sort: list[dict] | None, page: int, page_size: int, **common) -> tuple[dict, list[dict]]:
    """Products section plus repository warnings. `total` is the match count, not the page size.

    `common` is the filter set shared by the listing and its count, so the two cannot drift apart.
    """
    results, has_next_page, warnings = list_products(
        page=page,
        page_size=page_size,
        sort=sort or [{"relevance": "DESC"}],
        skus=None,
        url_key=None,
        product_type=None,
        on_stock=None,
        **common,
    )
    if _total_is_derivable(results, has_next_page, page):
        # Last page: the LIMIT+1 probe found nothing beyond it, so the offset gives the exact total.
        total = (page - 1) * page_size + len(results)
    else:
        # count_products repeats the filter warnings list_products already returned — drop them,
        # or every filter warning shows up twice from page 2 onwards.
        total, _ = count_products(**common)
    return {"total": total, "results": results, "has_next_page": has_next_page}, warnings


def _total_is_derivable(results: list, has_next_page: bool, page: int) -> bool:
    """True when the page itself pins the total, so no COUNT is needed.

    An empty page past the first says nothing about the total — the client asked for a page beyond
    the end, and the offset arithmetic would invent a count (page=99 → 196 matches that do not exist).
    """
    if has_next_page:
        return False
    return bool(results) or page == 1


def _search_categories(channel: Channel, language, query: str, limit: int) -> list[dict]:
    """FTS prefix match on category names."""
    try:
        from django_pim.models import ProductCategory
    except ImportError:
        return []

    lang_iso = language.iso2 if language else "en"

    categories = ProductCategory.objects.filter(
        shop__idx=channel.idx, is_active=True, is_in_menu=True, **{f"name_t9n__{lang_iso}__icontains": query}
    )[:limit]

    return [
        {
            "idx": cat.idx,
            "name": cat.name_lang(lang_iso),
            "url_key": cat.url_key_t9n.get(lang_iso, cat.idx),
            "image_url": cat.image_url or None,
            "products_count": 0,
        }
        for cat in categories
    ]


def _get_phrase_suggestions(channel: Channel, language, query: str, limit: int) -> list[dict]:
    """Phrase completions from product names via trigram similarity (pg_trgm)."""
    from django_matrix.models import ProductT9N

    lang_iso = language.iso2 if language else "en"

    # Simple prefix match for Phase 1 — pg_trgm fuzzy in Phase 2
    names = (
        ProductT9N.objects.filter(
            product_representation__channel__idx=channel.idx, language__iso2=lang_iso, name__icontains=query
        )
        .values_list("name", flat=True)
        .distinct()[:limit]
    )

    return [{"text": name, "type": "completion"} for name in names if name]
