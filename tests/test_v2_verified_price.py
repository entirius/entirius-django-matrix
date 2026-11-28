# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 ``products/`` and the verified-customer price rule: not implemented yet.

v1 applies ``is_only_for_verified_user`` (``tests/test_v1_verified_price.py``). v2 gets the rule together with
per-customer ``prices/``; see TODO(verified-price) in ``services/product_serializer.py``. The test below is a
strict xfail: it fails the suite the day the rule lands, so the marker and the TODO go away in the same change.
"""

import pytest

from django_matrix.models import ProductPrice

PRODUCTS = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL"


@pytest.fixture
def flagged_product(simple_product):
    ProductPrice.objects.filter(product_representation=simple_product).update(is_only_for_verified_user=True)
    return simple_product


@pytest.mark.xfail(strict=True, reason="TODO(verified-price): v2 does not apply is_only_for_verified_user yet")
def test_flagged_price_is_null_on_the_public_listing(api, flagged_product, channel_full):
    response = api.get(PRODUCTS)
    assert response.status_code == 200
    assert response.json()["results"][0]["price"] is None
