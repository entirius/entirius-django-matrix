# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Paging through a listing returns every product exactly once, even when products tie on every sort key."""

from decimal import Decimal

import pytest

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


@pytest.mark.parametrize(
    "sort",
    [None, [{"on_stock": "desc"}], [{"name": "asc"}], [{"price": "asc"}], [{"created": "desc"}]],
    ids=["default", "on_stock", "name", "price", "created"],
)
def test_the_tie_breaker_is_the_last_order_key(searchable_channel, sort):
    """Whether ties go wrong depends on the query plan, so the guarantee is asserted on the SQL too."""
    from django_matrix.repository.raw_sql.product import TIE_BREAKER, Product
    from django_matrix.utils.params import Query

    ch, lang, currency, country = searchable_channel
    ch.default_order = "on_stock"
    ch.save(update_fields=["default_order"])
    _, _, _, (sql, _), _ = Product().find_by_api_query(
        params=Query(page=1, limit=12, language=lang.iso2, currency=currency.iso3, country=country.iso2, sort=sort),
        channel=ch,
        language=lang,
        country=country,
        currency=currency,
        is_customer_verified=False,
        limit_offset=False,
        only_generate_sql=True,
    )
    assert sql.endswith(TIE_BREAKER)


def test_products_of_one_price_follow_the_next_sort_key(api, tied_products):
    from django_matrix.models import ProductT9N

    for t9n in ProductT9N.objects.select_related("product_representation"):
        t9n.name = f"Sofa {t9n.product_representation.sku}"
        t9n.save(update_fields=["name"])

    data = api.get(f"/api/matrix/v2/test-v2/products/?{QUERY}&page_size=3&s_price=asc&s_name=desc").json()

    assert [product["sku"] for product in data["results"]] == ["TIE-039", "TIE-038", "TIE-037"]
