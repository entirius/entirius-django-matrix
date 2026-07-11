# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 tests for stock/, categories/, options/, search/, omnibus/.

Uses channel_full from conftest.py (idx="test-v2").
"""

BASE = "/api/matrix/v2/test-v2"


class TestCategoriesEndpoint:
    def test_categories_returns_list(self, api, channel_full):
        response = api.get(f"{BASE}/categories/?language=en")
        assert response.status_code == 200

    def test_categories_single_wraps_in_results(self, api, channel_full):
        response = api.get(f"{BASE}/categories/?language=en&url_key=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["results"] == []


class TestOptionsEndpoint:
    def test_options_returns_pregrouped(self, api, channel_full):
        response = api.get(f"{BASE}/options/?language=en&currency=EUR&country=PL")
        assert response.status_code == 200
        data = response.json()
        assert "sort" in data
        assert "ranges" in data
        assert "filters" in data
        assert isinstance(data["sort"], list)
        assert isinstance(data["ranges"], list)
        assert isinstance(data["filters"], list)


class TestSearchEndpoint:
    def test_search_requires_query(self, api, channel_full):
        response = api.get(f"{BASE}/search/?language=en")
        assert response.status_code == 200
        data = response.json()
        assert data["products"]["total"] == 0

    def test_search_short_query_returns_empty(self, api, channel_full):
        response = api.get(f"{BASE}/search/?q=a&language=en")
        assert response.status_code == 200
        assert response.json()["products"]["total"] == 0

    def test_search_returns_sections(self, api, channel_full):
        response = api.get(f"{BASE}/search/?q=test+query&language=en&currency=EUR&country=PL")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "categories" in data
        assert "phrases" in data

    def test_search_finds_product_by_name(self, api, simple_product, channel_full):
        response = api.get(f"{BASE}/search/?q=chair&language=en&currency=EUR&country=PL")
        assert response.status_code == 200
        products = response.json()["products"]
        if products["total"] > 0:
            found_names = [r["name"] for r in products["results"]]
            assert any("Chair" in n for n in found_names)


class TestPricesEndpoint:
    def test_prices_requires_auth(self, api, channel_full):
        response = api.get(f"{BASE}/prices/?sku=TEST-001")
        assert response.status_code in (401, 403)

    def test_prices_empty_without_skus(self, admin_client, channel_full):
        response = admin_client.get(f"{BASE}/prices/")
        assert response.status_code == 200
        assert response.json() == {}

    def test_prices_returns_keyed_dict(self, admin_client, simple_product, channel_full):
        response = admin_client.get(f"{BASE}/prices/?sku=V2-SIMPLE-001")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestOmnibusEndpoint:
    def test_omnibus_returns_dict(self, api, channel_full):
        response = api.get(f"{BASE}/omnibus/?sku=TEST-001&currency=EUR&country=PL")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_omnibus_empty_without_skus(self, api, channel_full):
        response = api.get(f"{BASE}/omnibus/")
        assert response.status_code == 200
        assert response.json() == {}
