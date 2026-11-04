# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The listings answer with the default PAGINATION_TYPE (1, X_PAGES) when the page count runs on the request thread.

That happens with MATRIX_PRODUCTS_PARALLEL_QUERIES off, and with it on when the parallel queries fail (for example
"too many clients") and the listing falls back to running them one after the other. tests/settings.py sets
PAGINATION_TYPE = 0, so no other test reaches the count.
"""

from unittest.mock import patch

import pytest
from django.db import OperationalError

from django_matrix.enums import PaginationType

V1 = "/api/matrix/v1/test-v2/products/?language=en&currency=EUR&country=PL&limit=2"
V2 = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&page_size=2"


def parallel_queries_fail(*args, **kwargs):
    raise OperationalError("too many clients already")


@pytest.fixture(params=["parallel_off", "parallel_fallback"])
def count_on_the_request_thread(request):
    parallel = request.param == "parallel_fallback"
    with (
        patch("django_matrix.settings.PAGINATION_TYPE", PaginationType.X_PAGES),
        patch("django_matrix.repository.raw_sql.product.MATRIX_PRODUCTS_PARALLEL_QUERIES", parallel),
        patch(
            "django_matrix.repository.raw_sql.product.Product.execute_parallel_queries",
            side_effect=parallel_queries_fail,
        ),
    ):
        yield


def test_the_v1_listing_counts_its_pages(api, many_sofas, count_on_the_request_thread):
    response = api.get(V1)

    assert response.status_code == 200, response.content
    assert len(response.json()["data"]) == 2
    # X_PAGES answers floor(count / limit); the count covers the whole listing, as the parallel count does.
    assert response.json()["pagination"]["pages"] == 2


def test_the_v2_listing_answers(api, many_sofas, count_on_the_request_thread):
    response = api.get(V2)

    assert response.status_code == 200, response.content
    assert len(response.json()["results"]) == 2
    assert response.json()["has_next_page"] is True
