# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The v2 listing reads rows only: `has_next_page` comes from LIMIT page_size + 1, the total from `products/count/`.

`find_by_api_query` counts the whole listing for the v1 `pages` whenever PAGINATION_TYPE is X_PAGES (the default) or
FULL_PAGES. v2 threw that count away, and with MATRIX_PRODUCTS_PARALLEL_QUERIES it took a second connection for it.
"""

from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_matrix.enums import PaginationType
from django_matrix.repository.raw_sql.product import Product

QS = "?language=en&currency=EUR&country=PL"
V1 = f"/api/matrix/v1/test-v2/products/{QS}&limit=2"
V2 = f"/api/matrix/v2/test-v2/products/{QS}&page_size=2"
SEARCH = f"/api/matrix/v2/test-v2/search/{QS}&q=Sofa&page_size=2"


def run_in_turn(self, main_sql, main_params, count_sql, count_params):
    """The parallel queries, run on the request thread: a pool thread's connection cannot see the test transaction."""
    return self.fetch_all(main_sql, main_params), self.fetch_count(count_sql, count_params)


@pytest.fixture(params=[PaginationType.X_PAGES, PaginationType.FULL_PAGES], ids=["x_pages", "full_pages"])
def pagination_type(request):
    with patch("django_matrix.settings.PAGINATION_TYPE", request.param):
        yield request.param


@pytest.fixture(params=[False, True], ids=["parallel_off", "parallel_on"])
def parallel_queries(request):
    with (
        patch("django_matrix.repository.raw_sql.product.MATRIX_PRODUCTS_PARALLEL_QUERIES", request.param),
        patch.object(Product, "execute_parallel_queries", autospec=True, side_effect=run_in_turn) as spy,
    ):
        yield spy


def get_counting(api, url):
    with CaptureQueriesContext(connection) as queries:
        response = api.get(url)
    assert response.status_code == 200, response.content
    counts = [q["sql"] for q in queries.captured_queries if "count(*)" in q["sql"].lower()]
    return response.json(), counts


def test_the_v2_listing_runs_no_count(api, many_sofas, pagination_type, parallel_queries):
    body, counts = get_counting(api, V2)

    assert len(body["results"]) == 2
    assert body["has_next_page"] is True
    assert counts == []
    parallel_queries.assert_not_called()


def test_the_v2_search_counts_once(api, many_sofas, pagination_type, parallel_queries):
    body, counts = get_counting(api, SEARCH)

    assert body["products"]["total"] == 5
    assert len(counts) == 1
    parallel_queries.assert_not_called()


def test_the_v1_listing_still_counts_its_pages(api, many_sofas, pagination_type, parallel_queries):
    body, counts = get_counting(api, V1)

    assert len(body["data"]) == 2
    assert len(counts) == 1
    if pagination_type == PaginationType.X_PAGES:
        assert body["pagination"]["pages"] == 2  # floor(5 / 2)
    else:
        assert (body["pagination"]["pages"], body["pagination"]["count"]) == (3, 5)  # ceil(5 / 2), the total


@pytest.mark.parametrize("page", [1, 2, 3])
def test_the_v2_body_does_not_depend_on_the_pagination_type(api, many_sofas, parallel_queries, page):
    url = f"{V2}&page={page}&s_name=DESC"
    bodies = {}
    for pagination_type in (PaginationType.NONE, PaginationType.X_PAGES, PaginationType.FULL_PAGES):
        with patch("django_matrix.settings.PAGINATION_TYPE", pagination_type):
            bodies[pagination_type] = api.get(url).json()

    assert bodies[PaginationType.X_PAGES] == bodies[PaginationType.NONE]
    assert bodies[PaginationType.FULL_PAGES] == bodies[PaginationType.NONE]
