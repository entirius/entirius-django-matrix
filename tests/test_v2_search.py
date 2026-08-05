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


class TestSearchPageBounds:
    """`page` is 1-based. Anything below that would become a negative SQL OFFSET (HTTP 500)."""

    def test_page_zero_is_clamped(self, api, many_sofas):
        products = api.get(f"{BASE}{QS}&q=Sofa&page=0&page_size=2").json()["products"]
        assert products["total"] == 5
        assert len(products["results"]) == 2

    def test_negative_page_is_clamped(self, api, many_sofas):
        response = api.get(f"{BASE}{QS}&q=Sofa&page=-1&page_size=2")
        assert response.status_code == 200
        assert response.json()["products"]["total"] == 5


class TestSearchMinLength:
    """Query must be >= 2 chars."""

    def test_short_query_returns_empty(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=a").json()
        assert data["products"]["total"] == 0
        assert data["products"]["results"] == []

    def test_no_query_returns_empty(self, api, channel_full):
        data = api.get(f"{BASE}?language=en").json()
        assert data["products"]["total"] == 0

    def test_short_query_respects_scope(self, api, channel_full):
        """The short-query path must not return sections the caller did not ask for."""
        data = api.get(f"{BASE}{QS}&q=a&scope=products").json()
        assert "products" in data
        assert "categories" not in data

    def test_empty_query_returns_empty(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=").json()
        assert data["products"]["total"] == 0


class TestSearchFindsProduct:
    """Search against actual fixture data."""

    def test_search_finds_by_name(self, api, simple_product, searchable_channel):
        """Searching 'chair' should find 'Test Chair'."""
        products = api.get(f"{BASE}{QS}&q=chair").json()["products"]
        assert [r["sku"] for r in products["results"]] == ["V2-SIMPLE-001"]

    def test_search_result_has_core_fields(self, api, simple_product, searchable_channel):
        """Found product should have sku, name, url_key, price."""
        product = api.get(f"{BASE}{QS}&q=chair").json()["products"]["results"][0]
        for field in ("sku", "name", "url_key", "price"):
            assert field in product


class TestSearchTotal:
    """`total` is the match count. Regression: it used to be the page size."""

    def test_total_is_not_page_size(self, api, many_sofas):
        products = api.get(f"{BASE}{QS}&q=Sofa&page_size=2").json()["products"]
        assert products["total"] == 5
        assert len(products["results"]) == 2
        assert products["has_next_page"] is True

    def test_total_on_last_page(self, api, many_sofas):
        """Last page derives the total from the offset, no COUNT query."""
        products = api.get(f"{BASE}{QS}&q=Sofa&page=3&page_size=2").json()["products"]
        assert products["total"] == 5
        assert len(products["results"]) == 1
        assert products["has_next_page"] is False

    def test_total_is_stable_across_pages(self, api, many_sofas):
        totals = [api.get(f"{BASE}{QS}&q=Sofa&page={p}&page_size=2").json()["products"]["total"] for p in (1, 2, 3)]
        assert totals == [5, 5, 5]

    def test_total_on_page_past_the_end(self, api, many_sofas):
        """An empty page says nothing about the total — the offset must not invent one."""
        products = api.get(f"{BASE}{QS}&q=Sofa&page=99&page_size=2").json()["products"]
        assert products["results"] == []
        assert products["total"] == 5

    def test_total_is_zero_when_nothing_matches(self, api, many_sofas):
        products = api.get(f"{BASE}{QS}&q=zzznomatch").json()["products"]
        assert products["total"] == 0
        assert products["results"] == []

    def test_total_matches_count_endpoint(self, api, many_sofas):
        total = api.get(f"{BASE}{QS}&q=Sofa&page_size=2").json()["products"]["total"]
        count = api.get(f"/api/matrix/v2/test-v2/products/count/{QS}&search=Sofa").json()["count"]
        assert total == count

    def test_filter_warnings_are_not_duplicated_when_counting(self, api, many_sofas):
        """The COUNT path repeats the listing's warnings — they must not reach meta twice."""
        meta = api.get(f"{BASE}{QS}&q=Sofa&page_size=2&q_notafilter=x").json()["meta"]
        assert [w["code"] for w in meta["warnings"]].count("filter.not_filterable") == 1


class TestSearchRelevance:
    """Relevance ranks best matches first. Regression: the service asked for ASC."""

    def test_default_sort_is_relevance_desc(self, spy_list_products, channel_full):
        from django_matrix.services import search_service

        ch, lang, currency, country = channel_full
        search_service.search(
            channel=ch, language=lang, currency=currency, country=country, query="sofa", scope="products"
        )
        assert spy_list_products["sort"] == [{"relevance": "DESC"}]

    def test_explicit_sort_still_wins(self, spy_list_products, channel_full):
        from django_matrix.services import search_service

        ch, lang, currency, country = channel_full
        search_service.search(
            channel=ch,
            language=lang,
            currency=currency,
            country=country,
            query="sofa",
            scope="products",
            sort=[{"price": "ASC"}],
        )
        assert spy_list_products["sort"] == [{"price": "ASC"}]

    def test_name_match_outranks_tag_match(self, api, searchable_channel, fts_on):
        """End-to-end proof that search_rank DESC reaches the SQL (name weight B > tags weight D)."""
        from decimal import Decimal

        from django_matrix.models import ProductPrice, ProductRepresentation, ProductT9N

        ch, lang, currency, country = searchable_channel
        # SKU order would put the tag match first, so passing by accident is not possible.
        # `tags` is expanded with jsonb_array_elements_text, so it must be a flat array.
        for sku, name, tags in [("A-TAGGED", "Armchair", ["sofa"]), ("Z-NAMED", "Sofa", [])]:
            pr = ProductRepresentation.objects.create(
                sku=sku, channel=ch, product_type="SIMPLE", kind_of_product="PHYSICAL", on_stock=True, tags=tags
            )
            ProductT9N.objects.create(product_representation=pr, language=lang, name=name, url_key=name.lower())
            ProductPrice.objects.create(
                product_representation=pr,
                currency=currency,
                country=country,
                gross=Decimal("100.00"),
                net=Decimal("81.30"),
                final_gross=Decimal("100.00"),
                final_net=Decimal("81.30"),
            )

        results = api.get(f"{BASE}{QS}&q=sofa").json()["products"]["results"]
        assert [r["sku"] for r in results][0] == "Z-NAMED"


class TestSearchUnknownParams:
    """Unknown params warn, HTTP stays 200."""

    def test_unknown_param_warns(self, api, channel_full):
        meta = api.get(f"{BASE}{QS}&q=sofa&fbclid=xyz").json()["meta"]
        assert meta["status"] == "warning"
        assert [w["param"] for w in meta["warnings"]] == ["fbclid"]

    def test_limit_is_declared_here(self, api, channel_full):
        """`limit` is read by search/, unlike products/ — asserts the intended asymmetry."""
        assert api.get(f"{BASE}{QS}&q=sofa&limit=3").json()["meta"] == {"status": "ok", "warnings": []}

    def test_short_query_still_returns_meta(self, api, channel_full):
        data = api.get(f"{BASE}{QS}&q=a").json()
        assert data["meta"] == {"status": "ok", "warnings": []}

    def test_format_param_is_not_reported_as_unknown(self, api, channel_full):
        """DRF consumes ?format= for content negotiation — it is not ignored."""
        assert api.get(f"{BASE}{QS}&q=sofa&format=json").json()["meta"]["warnings"] == []

    def test_unknown_param_warnings_are_capped(self, api, channel_full):
        extra = "&".join(f"junk{n}=1" for n in range(30))
        warnings = api.get(f"{BASE}{QS}&q=sofa&{extra}").json()["meta"]["warnings"]
        assert len(warnings) == 11
        assert warnings[-1]["code"] == "param.unknown_truncated"

    def test_long_param_name_is_truncated(self, api, channel_full):
        name = "x" * 200
        warnings = api.get(f"{BASE}{QS}&q=sofa&{name}=1").json()["meta"]["warnings"]
        assert len(warnings[0]["param"]) == 64

    def test_short_query_warns_unknown_param(self, api, channel_full):
        meta = api.get(f"{BASE}{QS}&q=a&utm_source=x").json()["meta"]
        assert [w["param"] for w in meta["warnings"]] == ["utm_source"]


class TestSearchScope:
    def test_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent/search/?q=test&language=en")
        assert response.status_code == 404
