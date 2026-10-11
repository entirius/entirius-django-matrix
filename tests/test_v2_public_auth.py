# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public v2 views never evaluate credentials: no authentication class, whatever the service's default is."""

import base64

import pytest
from rest_framework.permissions import AllowAny

from django_matrix.api.v2 import urls as v2_urls
from django_matrix.api.v2.views.price_views import PricesView

PUBLIC_VIEWS = [p.callback.view_class for p in v2_urls.urlpatterns if p.callback.view_class is not PricesView]
PRODUCTS_URL = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL"


def _basic(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"HTTP_AUTHORIZATION": f"Basic {token}"}


def test_every_route_but_prices_is_public():
    assert len(PUBLIC_VIEWS) == len(v2_urls.urlpatterns) - 1 == 7


@pytest.mark.parametrize("view", PUBLIC_VIEWS, ids=lambda view: view.__name__)
def test_public_view_declares_no_authentication(view):
    assert view.authentication_classes == []
    assert view.permission_classes == [AllowAny]


def test_products_answer_the_same_for_any_basic_credentials(api, channel_full, regular_user):
    responses = [
        api.get(PRODUCTS_URL),
        api.get(PRODUCTS_URL, **_basic("user", "wrong-password")),
        api.get(PRODUCTS_URL, **_basic("user", "user123")),
    ]
    assert [r.status_code for r in responses] == [200, 200, 200]
    assert not [r for r in responses if "WWW-Authenticate" in r]
