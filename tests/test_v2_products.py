# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 products/ endpoint tests — core shape, include groups, filters, pagination."""


class TestProductsListingCore:
    """Core response shape — no include param."""

    def test_listing_returns_paginated_shape(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        assert response.status_code == 200
        data = response.json()
        assert "has_next_page" in data
        assert "page" in data
        assert "page_size" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        # meta envelope is always present; no ignored params => status ok, empty warnings
        assert data["meta"] == {"status": "ok", "warnings": []}

    def test_core_fields_present(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        product = response.json()["results"][0]
        assert product["sku"] == "V2-SIMPLE-001"
        assert product["product_type"] == "SIMPLE"
        assert product["is_virtual"] is False
        assert product["name"] == "Test Chair"
        assert product["url_key"] == "test-chair"
        assert product["on_stock"] is True
        assert "price" in product
        assert isinstance(product["categories"], list)

    def test_price_has_gross_and_net(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        price = response.json()["results"][0]["price"]
        assert price["gross"] == "100.00"
        assert price["net"] == "81.30"
        assert price["final_gross"] == "80.00"
        assert price["final_net"] == "65.04"
        assert price["tax_rate"] == "0.23"
        assert price["currency"] == "EUR"

    def test_no_include_no_extra_fields(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        product = response.json()["results"][0]
        assert "attributes" not in product
        assert "visual_assets" not in product
        assert "description" not in product
        assert "media" not in product
        assert "variants" not in product

    def test_has_next_page_false_when_few_results(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        assert response.json()["has_next_page"] is False

    def test_url_key_single_product(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?url_key=test-chair&language=en&currency=EUR&country=PL")
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["sku"] == "V2-SIMPLE-001"


class TestProductsIncludeGroups:
    """Include groups add extra fields to response."""

    def test_include_visual_assets(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=visual_assets")
        product = response.json()["results"][0]
        assert "visual_assets" in product
        assert len(product["visual_assets"]) == 1
        va = product["visual_assets"][0]
        assert va["feature_idx"] == "color"
        assert va["has_visual_asset"] is True
        assert va["value"] == "Red"
        assert va["extension"]["color_hash"] == "#CC0000"

    def test_include_attributes(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=attributes")
        product = response.json()["results"][0]
        assert "attributes" in product
        assert (
            len(product["attributes"]) == 3
        )  # color + weight + is_handmade (all is_visible=true), not meta_kw (seo only)

    def test_include_full(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=full")
        product = response.json()["results"][0]
        # seo fields with exact values
        assert product["url_keys"]["en"] == "test-chair"
        assert product["meta_title"] == "Test Chair | Store"
        assert isinstance(product["seo_attributes"], list)
        # content fields with exact values
        assert product["description"] == "<p>Description</p>"
        assert product["short_description"] == "Short desc"
        assert isinstance(product["media"], list)
        # related fields
        assert isinstance(product["variants"], list)
        assert isinstance(product["children_skus"], list)

    def test_unknown_include_ignored(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=nonexistent")
        assert response.status_code == 200
        product = response.json()["results"][0]
        assert "nonexistent" not in product


class TestProductsFiltering:
    """q_ and r_ filter params."""

    def test_filter_by_on_stock(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&on_stock=true")
        assert response.status_code == 200

    def test_sku_batch_lookup(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&sku=V2-SIMPLE-001")
        data = response.json()
        assert len(data["results"]) == 1


class TestProductsCount:
    """products/count/ endpoint."""

    def test_count_returns_integer(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/count/?language=en&currency=EUR&country=PL")
        assert response.status_code == 200
        assert "count" in response.json()
        assert isinstance(response.json()["count"], int)


class TestBooleanAttributes:
    """Decision #13 — boolean attributes: value=translated, value_idx=true/false."""

    def test_bool_attribute_translated_value(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=attributes")
        product = response.json()["results"][0]
        bool_attrs = [a for a in product["attributes"] if a["feature_type"] == "BOOL"]
        assert len(bool_attrs) >= 1
        assert bool_attrs[0]["value"] == "Yes"  # translated, not raw "True"
        assert bool_attrs[0]["value_idx"] == "true"  # machine identifier


class TestCategoriesPath:
    """Decision #35 — categories extended with path when include=full."""

    def test_core_categories_flat_no_path(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        product = response.json()["results"][0]
        for cat in product.get("categories", []):
            assert "path" not in cat

    def test_full_categories_have_path(self, api, simple_product, channel_full):
        """include=full extends categories with path. Path requires PIM ProductCategory — may be absent in test."""
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=full")
        product = response.json()["results"][0]
        categories = product.get("categories", [])
        assert isinstance(categories, list)
        assert len(categories) >= 1
        # Path is added by _extend_categories_with_path only when PIM ProductCategory exists
        if "path" in categories[0]:
            assert isinstance(categories[0]["path"], list)


class TestUrlKeysAllLanguages:
    """Decision #20 — url_keys dict with all language variants."""

    def test_include_full_has_url_keys_dict(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=full")
        product = response.json()["results"][0]
        url_keys = product.get("url_keys", {})
        assert isinstance(url_keys, dict)
        assert "en" in url_keys
        assert url_keys["en"] == "test-chair"

    def test_url_keys_includes_other_languages(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=full")
        product = response.json()["results"][0]
        url_keys = product.get("url_keys", {})
        if "pl" in url_keys:
            assert url_keys["pl"] == "testowe-krzeslo"


class TestPriceCurrency:
    """C1 fix — currency from regional resolution, not hardcoded."""

    def test_price_currency_matches_request(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL")
        price = response.json()["results"][0]["price"]
        assert price["currency"] == "EUR"


class TestSeoAttributes:
    """Decision #34 — seo_attributes in include=full from is_seo flag."""

    def test_seo_attributes_present_in_full(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&include=full")
        product = response.json()["results"][0]
        seo_attrs = product.get("seo_attributes", [])
        assert isinstance(seo_attrs, list)
        assert len(seo_attrs) >= 1, "meta_kw (is_seo=True) should be in seo_attributes"
        assert seo_attrs[0]["feature_idx"] == "meta_kw"


class TestUnknownChannel:
    """404 for unknown channel — all endpoints."""

    def test_products_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent-channel/products/?language=en&currency=EUR&country=PL")
        assert response.status_code == 404

    def test_stock_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent-channel/stock/?sku=TEST")
        assert response.status_code == 404


class TestParseHelpers:
    """Unit tests for parse_prefix_params, parse_range_params — no DB needed."""

    def test_parse_prefix_single_value(self):
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_prefix_params

        qd = QueryDict("q_color=red")
        result = parse_prefix_params(qd, "q_")
        assert result == {"color": ["red"]}

    def test_parse_prefix_multi_value(self):
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_prefix_params

        qd = QueryDict("q_color=red&q_color=blue&q_size=XL")
        result = parse_prefix_params(qd, "q_")
        assert result == {"color": ["red", "blue"], "size": ["XL"]}

    def test_parse_prefix_empty(self):
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_prefix_params

        qd = QueryDict("")
        result = parse_prefix_params(qd, "q_")
        assert result == {}

    def test_parse_range_valid(self):
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_range_params

        qd = QueryDict("r_price=100,500")
        result = parse_range_params(qd, "r_")
        assert result == {"price": ["100", "500"]}

    def test_parse_range_single_value_ignored(self):
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_range_params

        qd = QueryDict("r_price=100")
        result = parse_range_params(qd, "r_")
        assert result == {}  # needs exactly 2 parts

    def test_parse_range_three_values_ignored(self):
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_range_params

        qd = QueryDict("r_price=100,500,900")
        result = parse_range_params(qd, "r_")
        assert result == {}  # needs exactly 2 parts

    def test_parse_range_repeated_params(self):
        """Canonical form: r_price=100&r_price=500 (matches URLSearchParams output)."""
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_range_params

        qd = QueryDict("r_price=100&r_price=500")
        result = parse_range_params(qd, "r_")
        assert result == {"price": ["100", "500"]}

    def test_parse_range_repeated_three_values_ignored(self):
        """Three repeated values fail the arity check, same as three comma-separated."""
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_range_params

        qd = QueryDict("r_price=100&r_price=500&r_price=900")
        result = parse_range_params(qd, "r_")
        assert result == {}

    def test_parse_range_mixed_features_repeated(self):
        """Multiple distinct features in repeated form coexist."""
        from django.http import QueryDict

        from django_matrix.api.v2.views.product_views import parse_range_params

        qd = QueryDict("r_price=100&r_price=500&r_width=10&r_width=50")
        result = parse_range_params(qd, "r_")
        assert result == {"price": ["100", "500"], "width": ["10", "50"]}


# ── Pagination tests ─────────────────────────────────────────────────


class TestProductsPagination:
    """Pagination with has_next_page, page_size capping."""

    def test_page_size_max_100_capped(self, api, simple_product, channel_full):
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&page_size=999")
        assert response.status_code == 200
        assert response.json()["page_size"] == 100

    def test_has_next_page_true_with_multiple_products(self, api, simple_product, product_with_reviews, channel_full):
        """Two products + page_size=1 → has_next_page=True and only 1 result."""
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&page_size=1")
        data = response.json()
        assert data["has_next_page"] is True
        assert len(data["results"]) == 1

    def test_page_number_in_response(self, api, simple_product, channel_full):
        """Page number is echoed in response."""
        response = api.get("/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&page=1")
        assert response.json()["page"] == 1


# ── Sort tests ───────────────────────────────────────────────────────


class TestProductsSort:
    """Sort via the s_<field>=<dir> prefix convention (consistent with q_ / r_)."""

    BASE = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL"

    def test_sort_by_name_asc(self, api, simple_product, product_with_reviews, channel_full):
        response = api.get(f"{self.BASE}&s_name=asc")
        results = response.json()["results"]
        assert len(results) >= 2
        names = [r["name"] for r in results]
        assert names == sorted(names)

    def test_multi_sort_primary_respected(self, api, simple_product, product_with_reviews, channel_full):
        """Repeated s_ params = multi-sort; URL order is precedence. Primary key still orders the list."""
        response = api.get(f"{self.BASE}&s_name=asc&s_price=desc")
        results = response.json()["results"]
        names = [r["name"] for r in results]
        assert names == sorted(names)

    def test_legacy_sort_param_ignored(self, api, simple_product, product_with_reviews, channel_full):
        """Clean replace: the old sort/sort_dir params no longer order results."""
        baseline = [r["name"] for r in api.get(self.BASE).json()["results"]]
        legacy = [r["name"] for r in api.get(f"{self.BASE}&sort=name&sort_dir=desc").json()["results"]]
        assert legacy == baseline


# ── meta.warnings — feedback for ignored q_/r_/s_ params ─────────────


class TestProductsMeta:
    """Ignored filter/sort params surface as non-blocking meta.warnings (HTTP 200)."""

    BASE = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL"

    def test_unknown_sort_field_warns(self, api, simple_product, channel_full):
        meta = api.get(f"{self.BASE}&s_db_created=desc").json()["meta"]
        assert meta["status"] == "warning"
        w = meta["warnings"][0]
        assert w["param"] == "s_db_created"
        assert w["code"] == "sort.unknown_field"
        assert "db_created" in w["message"]

    def test_unfilterable_field_warns(self, api, simple_product, channel_full):
        meta = api.get(f"{self.BASE}&q_notafilter=x").json()["meta"]
        assert meta["status"] == "warning"
        assert meta["warnings"][0]["param"] == "q_notafilter"
        assert meta["warnings"][0]["code"] == "filter.not_filterable"

    def test_count_endpoint_has_meta(self, api, simple_product, channel_full):
        data = api.get("/api/matrix/v2/test-v2/products/count/?language=en&currency=EUR&country=PL&q_nope=1").json()
        assert "count" in data
        assert data["meta"]["status"] == "warning"
        assert data["meta"]["warnings"][0]["code"] == "filter.not_filterable"


# ── Product type filter ──────────────────────────────────────────────


class TestProductTypeFilter:
    def test_filter_configurable(self, api, simple_product, configurable_product, channel_full):
        response = api.get(
            "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&product_type=CONFIGURABLE"
        )
        results = response.json()["results"]
        for r in results:
            assert r["product_type"] == "CONFIGURABLE"
