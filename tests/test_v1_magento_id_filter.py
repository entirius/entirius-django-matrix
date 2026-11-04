# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v1 `products/?magento_id=` returns the products with those Magento ids, in the order the request names them.

The Magento search listing (`products_m2/`) goes through the same filter with the ids Magento returns.
"""

from unittest.mock import patch
from urllib.parse import urlencode

import pytest

LISTING = "/api/matrix/v1/test-v2/products/"
REGION = [("language", "en"), ("currency", "EUR"), ("country", "PL")]
MAGENTO_IDS = {"MG-101": 101, "MG-102": 102, "MG-103": 103, "MG-NONE": None}


@pytest.fixture
def magento_products(channel_full):
    from django_matrix.models import ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full
    for sku, magento_id in MAGENTO_IDS.items():
        pr = ProductRepresentation.objects.create(
            sku=sku,
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
            on_stock=True,
            magento_id=magento_id,
            url_keys={sku.lower(): "en"},
        )
        ProductT9N.objects.create(product_representation=pr, language=lang, name=sku, url_key=sku.lower())


def listing(api, *magento_ids):
    response = api.get(f"{LISTING}?{urlencode([*REGION, *(('magento_id', value) for value in magento_ids)])}")
    assert response.status_code == 200, response.content
    return [product["sku"] for product in response.json()["data"]]


@pytest.mark.parametrize(
    "magento_ids, skus",
    [
        (["103", "101"], ["MG-103", "MG-101"]),
        (["101", "103"], ["MG-101", "MG-103"]),
        (["102"], ["MG-102"]),
    ],
)
def test_the_filter_returns_the_products_in_the_requested_order(api, magento_products, magento_ids, skus):
    assert listing(api, *magento_ids) == skus


@pytest.mark.parametrize(
    "value",
    [
        "101) OR (1=1",
        "1' OR '1'='1",
        "101]::integer[], pr.magento_id) --",
        '"; SELECT pg_sleep(1); --',
        "99999999999",
        "",
    ],
)
def test_a_value_that_is_no_magento_id_matches_nothing(api, magento_products, value):
    assert listing(api, "102", value) == ["MG-102"]
    assert listing(api, value) == []


def test_the_magento_search_listing_keeps_the_order_magento_returned(api, magento_products):
    with patch("django_matrix.views.search.listing.get_id_list_from_magento", return_value=([103, 101], 2)):
        response = api.get(f"/api/matrix/v1/test-v2/products_m2/?{urlencode([*REGION, ('search_text', 'mg')])}")

    assert response.status_code == 200, response.content
    assert [product["sku"] for product in response.json()["data"]] == ["MG-103", "MG-101"]


def test_no_request_value_is_written_into_the_sql(channel_full):
    from django_matrix.repository.raw_sql.product import Product
    from django_matrix.utils.params import Query

    ch, lang, currency, country = channel_full
    value = "7) OR (1=1"
    _, _, _, (sql, params), _ = Product().find_by_api_query(
        params=Query(language=lang.iso2, currency=currency.iso3, country=country.iso2, magento_id=["3", value]),
        channel=ch,
        language=lang,
        country=country,
        currency=currency,
        is_customer_verified=False,
        only_generate_sql=True,
    )
    assert value not in sql
    assert "magento_id" in sql
    assert params["magento_id"] == [3]
