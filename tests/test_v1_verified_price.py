# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v1 ``products/?fetch_full_data=true`` follows the verified-customer price rule.

A price row flagged ``is_only_for_verified_user`` is shown to verified customers only: the full-data
``price`` block is ``None`` for everyone else, the same as ``final_price`` and ``price_range``.
"""

from types import SimpleNamespace

import pytest

from django_matrix.models import ProductPrice

FULL_DATA = "/api/matrix/v1/test-v2/products/?language=en&currency=EUR&country=PL&fetch_full_data=true"
NO_PRICE_RANGE = {"from": None, "to": None}


@pytest.fixture
def flagged_product(simple_product):
    ProductPrice.objects.filter(product_representation=simple_product).update(is_only_for_verified_user=True)
    return simple_product


def _log_in_customer(monkeypatch, is_verified: bool) -> None:
    """Make the v1 optional authentication resolve a customer, as a valid JWT would."""
    user = SimpleNamespace(is_authenticated=True, customer=SimpleNamespace(is_verified=is_verified, group=None))
    monkeypatch.setattr("django_utils.api.decorators.auth.authenticate", lambda request: user)


def _listed_product(api) -> dict:
    response = api.get(FULL_DATA)
    assert response.status_code == 200
    return response.json()["data"][0]


def _assert_no_price(product: dict) -> None:
    assert product["price"] is None
    assert product["final_price"] is None
    assert product["price_range"] == NO_PRICE_RANGE


def _assert_price(product: dict) -> None:
    assert product["price"] is not None
    assert product["price"]["sku"] == "V2-SIMPLE-001"
    assert float(product["price"]["price"]) == 100.0
    assert float(product["final_price"]) == 80.0


class TestFlaggedProductFullData:
    def test_anonymous_gets_no_price(self, api, flagged_product):
        _assert_no_price(_listed_product(api))

    def test_unverified_customer_gets_no_price(self, api, flagged_product, monkeypatch):
        _log_in_customer(monkeypatch, is_verified=False)
        _assert_no_price(_listed_product(api))

    def test_verified_customer_gets_price(self, api, flagged_product, monkeypatch):
        _log_in_customer(monkeypatch, is_verified=True)
        _assert_price(_listed_product(api))


class TestUnflaggedProductFullData:
    def test_anonymous_gets_price(self, api, simple_product):
        _assert_price(_listed_product(api))

    def test_unverified_customer_gets_price(self, api, simple_product, monkeypatch):
        _log_in_customer(monkeypatch, is_verified=False)
        _assert_price(_listed_product(api))

    def test_verified_customer_gets_price(self, api, simple_product, monkeypatch):
        _log_in_customer(monkeypatch, is_verified=True)
        _assert_price(_listed_product(api))
