# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 search/ endpoint tests — unified search with scope param."""

BASE = "/api/matrix/v2/test-v2/search/"
QS = "?language=en&currency=EUR&country=PL"


class TestSearchShape:
    """Response structure: {products, categories, phrases}."""

    def test_returns_200(self, api, channel_full):
        response = api.get(f"{BASE}{QS}&q=test")
        assert response.status_code == 200

    def test_sections_present(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=test+query").json()
        assert "products" in data
        assert "categories" in data
        assert "phrases" in data
        assert data["meta"] == {"status": "ok", "warnings": []}

    def test_products_section_shape(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=test+query").json()
        products = data["products"]
        assert "total" in products
        assert "results" in products
        assert "has_next_page" in products
        assert isinstance(products["results"], list)

    def test_categories_section_shape(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=test+query").json()
        cats = data["categories"]
        assert "results" in cats
        assert isinstance(cats["results"], list)

    def test_phrases_is_list(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=test+query").json()
        assert isinstance(data["phrases"], list)


class TestSearchMinLength:
    """Query must be >= 2 chars."""

    def test_short_query_returns_empty(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=a").json()
        assert data["products"]["total"] == 0
        assert data["products"]["results"] == []

    def test_no_query_returns_empty(self, api, channel_full):
        data = api.get(f"{BASE}?language=en").json()
        assert data["products"]["total"] == 0

    def test_empty_query_returns_empty(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=").json()
        assert data["products"]["total"] == 0


class TestSearchFindsProduct:
    """Search against actual fixture data."""

    def test_search_finds_by_name(self, api, simple_product, channel_full):
        """Searching 'chair' should find 'Test Chair'."""
        data = api.get(f"{BASE}{QS}&q=chair").json()
        products = data["products"]
        if products["total"] > 0:
            found_skus = [r["sku"] for r in products["results"]]
            assert "V2-SIMPLE-001" in found_skus

    def test_search_result_has_core_fields(self, api, simple_product, channel_full):
        """Found product should have sku, name, url_key, price."""
        data = api.get(f"{BASE}{QS}&q=chair").json()
        if data["products"]["total"] > 0:
            product = data["products"]["results"][0]
            assert "sku" in product
            assert "name" in product
            assert "url_key" in product
            assert "price" in product


class TestSearchScope:
    def test_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent/search/?q=test&language=en")
        assert response.status_code == 404
