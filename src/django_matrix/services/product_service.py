# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Product service — wraps repository layer for v2 API. No HTTP concerns."""

from django_matrix.models import Channel
from django_matrix.repository.raw_sql.product import Product as ProductRepository


def list_products(
    channel: Channel,
    language,
    currency,
    country,
    page: int = 1,
    page_size: int = 12,
    category: str | None = None,
    skus: list[str] | None = None,
    url_key: str | None = None,
    product_type: str | None = None,
    on_stock: bool | None = None,
    sort: list[dict] | None = None,
    filters: dict | None = None,
    ranges: dict | None = None,
    search: str | None = None,
) -> tuple[list[dict], bool, list[dict]]:
    """Returns (results, has_next_page, warnings). Queries LIMIT+1 to determine has_next_page without COUNT.

    `warnings` is a list of `{code, param, message}` for any q_/r_/s_ param the backend ignored.
    """
    from django_matrix.utils.params import Query

    params = Query(
        page=page,
        limit=page_size + 1,
        page_size=page_size,
        language=language.iso2 if language else None,
        currency=currency.iso3 if currency else None,
        country=country.iso2 if country else None,
        category_url_key=category,
        sku=skus,
        url_key=[url_key] if url_key else None,
        type=product_type,
        on_stock=on_stock,
        sort=sort,
        search=[search] if search else None,
        query=build_query_filters(filters) if filters else None,
        range=build_range_filters(ranges) if ranges else None,
    )

    results, _, _, _, warnings = ProductRepository().find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=False,
    )

    has_next_page = len(results) > page_size
    if has_next_page:
        results = results[:page_size]

    return results, has_next_page, warnings


def count_products(
    channel: Channel,
    language,
    currency,
    country,
    category: str | None = None,
    skus: list[str] | None = None,
    product_type: str | None = None,
    on_stock: bool | None = None,
    filters: dict | None = None,
    ranges: dict | None = None,
    search: str | None = None,
) -> tuple[int, list[dict]]:
    """Returns (count, warnings) for products matching filters."""
    from django_matrix.utils.params import Query

    params = Query(
        page=1,
        limit=1,
        language=language.iso2 if language else None,
        currency=currency.iso3 if currency else None,
        country=country.iso2 if country else None,
        category_url_key=category,
        sku=skus,
        type=product_type,
        on_stock=on_stock,
        search=[search] if search else None,
        query=build_query_filters(filters) if filters else None,
        range=build_range_filters(ranges) if ranges else None,
    )

    # Use only_generate_sql to get WHERE clause, then count via subquery — no row materialization
    repo = ProductRepository()
    _, _, _, (sql, sql_params), warnings = repo.find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=False,
        only_generate_sql=True,
        only_generate_minimal_sql=True,
    )
    return repo.count_full_pages(sql, sql_params), warnings


def build_query_filters(filters: dict) -> list[dict]:
    """Convert {feature_idx: [values]} dict to v1 query format."""
    return [{k: v} for k, v in filters.items()]


def build_range_filters(ranges: dict) -> list[dict]:
    """Convert {feature_idx: (from, to)} dict to v1 range format."""
    return [{k: v} for k, v in ranges.items()]
