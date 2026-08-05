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


# ── Search on the listing (33731) ────────────────────────────────────


class TestProductsSearch:
    """`?search=` narrows the listing. Regression: v2 used to drop the param silently."""

    BASE = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL"
    COUNT = "/api/matrix/v2/test-v2/products/count/?language=en&currency=EUR&country=PL"

    def test_search_narrows_results(self, api, simple_product, product_with_reviews, searchable_channel):
        skus = [r["sku"] for r in api.get(f"{self.BASE}&search=Reviewed").json()["results"]]
        assert skus == ["V2-REVIEW-001"]

    def test_search_matches_both_on_shared_term(self, api, simple_product, product_with_reviews, searchable_channel):
        skus = {r["sku"] for r in api.get(f"{self.BASE}&search=Chair").json()["results"]}
        assert skus == {"V2-SIMPLE-001", "V2-REVIEW-001"}

    def test_search_no_match_returns_empty(self, api, simple_product, searchable_channel):
        assert api.get(f"{self.BASE}&search=zzznomatch").json()["results"] == []

    def test_search_by_sku(self, api, simple_product, searchable_channel):
        """`sku` is searchable on every channel, no SearchableFeatures row needed."""
        skus = [r["sku"] for r in api.get(f"{self.BASE}&search=V2-SIMPLE").json()["results"]]
        assert skus == ["V2-SIMPLE-001"]

    def test_blank_search_is_not_a_filter(self, api, simple_product, product_with_reviews, searchable_channel):
        """`?search=` and `?search=%20` mean 'no search', not `ILIKE '% %'`."""
        unfiltered = len(api.get(self.BASE).json()["results"])
        assert len(api.get(f"{self.BASE}&search=").json()["results"]) == unfiltered
        assert len(api.get(f"{self.BASE}&search=%20").json()["results"]) == unfiltered

    def test_count_respects_search(self, api, simple_product, product_with_reviews, searchable_channel):
        """The bug this catches: count_products had no `search` kwarg at all."""
        assert api.get(f"{self.COUNT}&search=Reviewed").json()["count"] == 1
        assert api.get(f"{self.COUNT}&search=Chair").json()["count"] == 2

    def test_count_matches_listing(self, api, many_sofas, searchable_channel):
        listed = api.get(f"{self.BASE}&search=Sofa&page_size=100").json()["results"]
        assert api.get(f"{self.COUNT}&search=Sofa").json()["count"] == len(listed)

    def test_search_keeps_default_order_without_fts(self, api, many_sofas, searchable_channel):
        """FTS off (the default): search only shrinks the set, the order stays channel default."""
        unfiltered = [r["sku"] for r in api.get(f"{self.BASE}&page_size=100").json()["results"]]
        searched = [r["sku"] for r in api.get(f"{self.BASE}&search=Sofa&page_size=100").json()["results"]]
        assert searched == [sku for sku in unfiltered if sku in set(searched)]

    def test_search_combines_with_filters(self, api, many_sofas, searchable_channel):
        data = api.get(f"{self.BASE}&search=Sofa&on_stock=true&page_size=100").json()
        assert len(data["results"]) == 5
        assert data["meta"]["status"] == "ok"

    def test_search_and_product_type_narrow_together(
        self, api, simple_product, configurable_product, searchable_channel
    ):
        """AND semantics: a search that matches both types, narrowed to one."""
        data = api.get(f"{self.BASE}&search=Chair&product_type=CONFIGURABLE&page_size=100").json()
        assert data["results"] == []

    def test_page_below_one_is_clamped(self, api, many_sofas, searchable_channel):
        """`?page=0` / negatives would become a negative SQL OFFSET (HTTP 500)."""
        for page in (0, -1):
            response = api.get(f"{self.BASE}&search=Sofa&page={page}&page_size=2")
            assert response.status_code == 200
            assert len(response.json()["results"]) == 2

    def test_format_param_is_not_reported_as_unknown(self, api, simple_product, channel_full):
        assert api.get(f"{self.BASE}&format=json").json()["meta"]["warnings"] == []


# ── Unknown query params (33731) ─────────────────────────────────────


class TestUnknownParams:
    """Unknown params warn, never reject — consumers forward whole query strings."""

    BASE = "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL"

    def test_tracking_param_warns_without_failing(self, api, simple_product, channel_full):
        response = api.get(f"{self.BASE}&utm_source=google")
        assert response.status_code == 200
        meta = response.json()["meta"]
        assert meta["status"] == "warning"
        assert meta["warnings"][0] == {
            "code": "param.unknown",
            "param": "utm_source",
            "message": "unknown query param 'utm_source' was ignored",
        }

    def test_limit_is_not_an_alias_for_page_size(self, api, simple_product, channel_full):
        """v2 reads `page_size`. `limit` is v1 naming and is reported, not silently honoured."""
        data = api.get(f"{self.BASE}&limit=1&page_size=100").json()
        assert len(data["results"]) > 0
        assert [w["param"] for w in data["meta"]["warnings"]] == ["limit"]

    def test_repository_and_view_warnings_merge(self, api, simple_product, channel_full):
        meta = api.get(f"{self.BASE}&q_notafilter=x&gclid=abc").json()["meta"]
        assert [w["code"] for w in meta["warnings"]] == ["filter.not_filterable", "param.unknown"]

    def test_dynamic_prefixes_never_warn_as_unknown(self, api, simple_product, channel_full):
        meta = api.get(f"{self.BASE}&q_color=red&r_price=1&r_price=2&s_name=asc").json()["meta"]
        assert all(w["code"] != "param.unknown" for w in meta["warnings"])

    def test_full_declared_param_set_is_clean(self, api, simple_product, channel_full):
        """Anti-drift: fails the moment a param is read in get() without being declared."""
        params = (
            "&page=1&page_size=12&include=full&category=x&search=y&url_key=z&sku=A&product_type=SIMPLE&on_stock=true"
        )
        assert api.get(f"{self.BASE}{params}").json()["meta"] == {"status": "ok", "warnings": []}

    def test_count_endpoint_warns_too(self, api, simple_product, channel_full):
        base = "/api/matrix/v2/test-v2/products/count/?language=en&currency=EUR&country=PL"
        assert [w["param"] for w in api.get(f"{base}&utm_source=x").json()["meta"]["warnings"]] == ["utm_source"]

    def test_page_size_is_unknown_on_count(self, api, simple_product, channel_full):
        """count/ has no pagination, so page_size there is a client mistake worth reporting."""
        base = "/api/matrix/v2/test-v2/products/count/?language=en&currency=EUR&country=PL"
        assert [w["param"] for w in api.get(f"{base}&page_size=10").json()["meta"]["warnings"]] == ["page_size"]


# ── Product type filter ──────────────────────────────────────────────


class TestProductTypeFilter:
    def test_filter_configurable(self, api, simple_product, configurable_product, channel_full):
        response = api.get(
            "/api/matrix/v2/test-v2/products/?language=en&currency=EUR&country=PL&product_type=CONFIGURABLE"
        )
        results = response.json()["results"]
        for r in results:
            assert r["product_type"] == "CONFIGURABLE"
