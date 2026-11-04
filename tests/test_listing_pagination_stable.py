# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Paging through a listing returns every product exactly once, even when products tie on every sort key."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import connection

QUERY = "language=en&currency=EUR&country=PL"
TOTAL = 40


@pytest.fixture
def tied_products(searchable_channel):
    """Products equal on everything but the SKU, on a channel whose default order ties them all."""
    from django_matrix.models import ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = searchable_channel
    ch.default_order = "on_stock"
    ch.save(update_fields=["default_order"])
    for n in range(TOTAL):
        pr = ProductRepresentation.objects.create(
            sku=f"TIE-{n:03d}",
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
            on_stock=True,
            url_keys={f"tie-{n}": "en"},
        )
        ProductT9N.objects.create(product_representation=pr, language=lang, name="Sofa", url_key=f"tie-{n}")
        ProductPrice.objects.create(
            product_representation=pr,
            currency=currency,
            country=country,
            gross=Decimal("100.00"),
            net=Decimal("81.30"),
            final_gross=Decimal("100.00"),
            final_net=Decimal("81.30"),
        )


def walk(api, extra, page_size):
    skus = []
    for page in range(1, TOTAL + 2):
        data = api.get(f"/api/matrix/v2/test-v2/products/?{QUERY}&page={page}&page_size={page_size}{extra}").json()
        skus.extend(product["sku"] for product in data["results"])
        if not data["has_next_page"]:
            return skus
    pytest.fail("the listing never reached its last page")


@pytest.mark.parametrize("page_size", [7, 12, 16])
@pytest.mark.parametrize(
    "extra",
    ["", "&s_on_stock=desc", "&s_name=asc", "&s_price=asc", "&search=Sofa", "&search=Sofa&s_on_stock=desc"],
    ids=["default", "on_stock", "name", "price", "search", "search_on_stock"],
)
def test_every_product_comes_once(api, tied_products, extra, page_size):
    skus = walk(api, extra, page_size)
    assert len(skus) == TOTAL
    assert len(set(skus)) == TOTAL


def find(channel_full, sort=None, **kwargs):
    from django_matrix.repository.raw_sql.product import Product
    from django_matrix.utils.params import Query

    ch, lang, currency, country = channel_full
    return Product().find_by_api_query(
        params=Query(page=1, limit=12, language=lang.iso2, currency=currency.iso3, country=country.iso2, sort=sort),
        channel=ch,
        language=lang,
        country=country,
        currency=currency,
        is_customer_verified=False,
        **kwargs,
    )


def listing_sql(channel_full, sort=None, **kwargs):
    _, _, _, (sql, params), _ = find(channel_full, sort, only_generate_sql=True, **kwargs)
    return sql, params


def on_stock_by_default(channel_full, direction="ASC"):
    ch = channel_full[0]
    ch.default_order = "on_stock"
    ch.default_order_direction = direction
    ch.save(update_fields=["default_order", "default_order_direction"])


@pytest.mark.parametrize(
    "sort, direction",
    [
        (None, "ASC"),
        ([{"on_stock": "DESC"}], "DESC"),
        ([{"name": "ASC"}], "ASC"),
        ([{"price": "ASC"}], "ASC"),
        ([{"created": "DESC"}], "DESC"),
        ([{"price": "DESC"}, {"name": "ASC"}], "DESC"),
    ],
    ids=["default", "on_stock", "name", "price", "created", "price_then_name"],
)
def test_the_tie_breaker_is_the_last_order_key(searchable_channel, sort, direction):
    """Whether ties go wrong depends on the query plan, so the guarantee is asserted on the SQL too.

    The tie-breaker runs in the direction of the first key, so an index on (channel, first key, id) can serve it.
    """
    on_stock_by_default(searchable_channel)
    sql, _ = listing_sql(searchable_channel, sort, limit_offset=False)
    assert sql.endswith(f"pr.id {direction} ")


def test_the_tie_breaker_follows_a_descending_channel_default(searchable_channel):
    on_stock_by_default(searchable_channel, "DESC")
    sql, _ = listing_sql(searchable_channel, limit_offset=False)
    assert sql.endswith("pr.id DESC ")


@pytest.mark.parametrize("direction", ["ASC", "DESC"])
def test_a_page_of_the_default_on_stock_order_reads_an_index(searchable_channel, direction):
    """On a 60k-product channel page 1 takes 0.1 ms read from idx_product_channel_stock_id and 83 ms when Postgres
    sorts the channel. With sorting disabled the plan shows whether an index can deliver the order at all."""
    on_stock_by_default(searchable_channel, direction)
    sql, params = listing_sql(searchable_channel)
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_sort = off")
        cursor.execute("SET LOCAL enable_incremental_sort = off")
        cursor.execute(f"EXPLAIN {sql}", params)
        plan = "\n".join(row[0] for row in cursor.fetchall())
    assert "idx_product_channel_stock_id" in plan
    assert "Sort" not in plan


def test_the_count_counts_the_listing_without_sorting_it(searchable_channel, tied_products):
    from django_matrix.enums import PaginationType
    from django_matrix.repository.raw_sql import DbConnect

    counted = []
    fetch_count = DbConnect.fetch_count

    def spy(self, sql, params):
        counted.append(sql)
        return fetch_count(self, sql, params)

    with (
        patch.object(DbConnect, "fetch_count", spy),
        patch("django_matrix.settings.PAGINATION_TYPE", PaginationType.FULL_PAGES),
    ):
        products, count, *_ = find(searchable_channel)

    assert count == TOTAL
    assert len(products) == 12
    assert "ORDER BY" not in counted[0]


def test_products_of_one_price_follow_the_next_sort_key(api, tied_products):
    from django_matrix.models import ProductT9N

    for t9n in ProductT9N.objects.select_related("product_representation"):
        t9n.name = f"Sofa {t9n.product_representation.sku}"
        t9n.save(update_fields=["name"])

    data = api.get(f"/api/matrix/v2/test-v2/products/?{QUERY}&page_size=3&s_price=asc&s_name=desc").json()

    assert [product["sku"] for product in data["results"]] == ["TIE-039", "TIE-038", "TIE-037"]


@pytest.mark.parametrize("magento_id", [None, [7, 3]], ids=["no_default_order", "magento_ids"])
def test_a_listing_without_the_default_order_ends_with_the_tie_breaker(searchable_channel, magento_id):
    """The Magento search and suggest listings skip the default order: their pages need the tie-breaker too."""
    from django_matrix.repository.raw_sql.product import Product
    from django_matrix.utils.params import Query

    ch, lang, currency, country = searchable_channel
    _, _, _, (sql, _), _ = Product().find_by_api_query(
        params=Query(
            page=1, limit=12, language=lang.iso2, currency=currency.iso3, country=country.iso2, magento_id=magento_id
        ),
        channel=ch,
        language=lang,
        country=country,
        currency=currency,
        is_customer_verified=False,
        apply_default_order=False,
        limit_offset=False,
        only_generate_sql=True,
    )
    assert sql.endswith("pr.id ASC ")
