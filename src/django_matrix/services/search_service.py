# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Search service — unified search (Phase 1: products + categories)."""

from django_matrix.models import Channel
from django_matrix.services.meta import build_meta
from django_matrix.services.product_service import list_products


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
) -> dict:
    """Unified search. Returns sections based on scope param."""
    scopes = {s.strip() for s in scope.split(",")}
    result = {}
    warnings: list[dict] = []

    if "products" in scopes:
        results, has_next_page, warnings = list_products(
            channel=channel,
            language=language,
            currency=currency,
            country=country,
            page=page,
            page_size=page_size,
            category=category,
            sort=sort or [{"relevance": "ASC"}],
            filters=filters,
            ranges=ranges,
            search=query,
            skus=None,
            url_key=None,
            product_type=None,
            on_stock=None,
        )
        result["products"] = {"total": len(results), "results": results, "has_next_page": has_next_page}

    if "categories" in scopes:
        result["categories"] = {"results": _search_categories(channel, language, query, limit)}

    result["phrases"] = _get_phrase_suggestions(channel, language, query, limit)
    result["meta"] = build_meta(warnings)

    return result


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
