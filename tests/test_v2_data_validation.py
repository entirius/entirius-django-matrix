# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 data validation — asserts exact field values from fixtures through the full stack.

Every test here compares an HTTP response value against the known fixture value.
Catches bugs where fields are present but empty, wrong type, or unparsed JSON strings.
"""

BASE = "/api/matrix/v2/test-v2/products/"
QS = "?language=en&currency=EUR&country=PL"


def _get_product(api, extra_qs=""):
    response = api.get(f"{BASE}{QS}{extra_qs}")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) >= 1
    return results[0]


# ── Core field value assertions ──────────────────────────────────────


class TestCoreFieldValues:
    """Exact value match for every core product field against fixture data."""

    def test_url_key_matches_t9n(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert product["url_key"] == "test-chair"

    def test_name_matches_t9n(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert product["name"] == "Test Chair"

    def test_sku_exact(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert product["sku"] == "V2-SIMPLE-001"

    def test_product_type_exact(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert product["product_type"] == "SIMPLE"

    def test_is_virtual_false_for_physical(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert product["is_virtual"] is False

    def test_on_stock_true(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert product["on_stock"] is True

    def test_categories_parsed_not_string(self, api, simple_product, channel_full):
        product = _get_product(api)
        cats = product["categories"]
        assert isinstance(cats, list), f"categories should be list, got {type(cats)}"
        assert len(cats) >= 1
        assert cats[0]["idx"] == "chairs"
        assert cats[0]["name"] == "Chairs"
        assert cats[0]["url_key"] == "chairs"

    def test_badges_parsed_from_json(self, api, simple_product, channel_full):
        product = _get_product(api)
        badges = product["badges"]
        assert isinstance(badges, list), f"badges should be list, got {type(badges)}"
        assert len(badges) >= 1
        assert badges[0]["idx"] == "new"
        assert badges[0]["name"] == "New"

    def test_brands_parsed_from_json(self, api, simple_product, channel_full):
        product = _get_product(api)
        brands = product["brands"]
        assert isinstance(brands, list), f"brands should be list, got {type(brands)}"
        assert len(brands) >= 1
        assert brands[0]["idx"] == "brand-a"
        assert brands[0]["name"] == "Brand A"

    def test_feature_set_parsed(self, api, simple_product, channel_full):
        product = _get_product(api)
        fs = product["feature_set"]
        assert isinstance(fs, dict), f"feature_set should be dict, got {type(fs)}"
        assert fs["idx"] == "furniture"
        assert fs["name"] == "Furniture"

    def test_subnames_present(self, api, simple_product, channel_full):
        product = _get_product(api)
        # Fixture doesn't set subnames — should be null or empty, not missing
        assert "subnames" in product

    def test_null_fields_are_null(self, api, simple_product, channel_full):
        """Simple product has no parent and no reviews."""
        product = _get_product(api)
        assert product["parent_sku"] is None
        assert product["parent_url_key"] is None
        assert product["review_rating"] is None
        assert product["review_count"] is None

    def test_main_image_structure(self, api, simple_product, channel_full):
        """Simple product has main_image with source_set and alt_text."""
        product = _get_product(api)
        assert product["main_image"] is not None
        assert "source_set" in product["main_image"]
        assert product["main_image"]["alt_text"] == "Test Chair front view"


# ── Price exact value assertions ─────────────────────────────────────


class TestPriceExactValues:
    """Price fields must be exact Decimal strings matching fixture values."""

    def test_price_currency_eur(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["currency"] == "EUR"

    def test_price_gross_exact_decimal_string(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["gross"] == "100.00", f"Expected '100.00', got {price['gross']!r}"

    def test_price_net_exact(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["net"] == "81.30", f"Expected '81.30', got {price['net']!r}"

    def test_price_final_gross_exact(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["final_gross"] == "80.00"

    def test_price_final_net_exact(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["final_net"] == "65.04"

    def test_price_special_gross_exact(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["special_gross"] == "80.00"

    def test_price_special_net_exact(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["special_net"] == "65.04"

    def test_price_percent_off_is_int_20(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["percent_off"] == 20
        assert isinstance(price["percent_off"], int)

    def test_price_tax_rate_and_flags(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["tax_rate"] == "0.23"
        assert price["has_special_price"] is True
        assert price["is_range"] is False

    def test_price_range_fields_null_for_simple(self, api, simple_product, channel_full):
        price = _get_product(api)["price"]
        assert price["range_from_gross"] is None
        assert price["range_to_gross"] is None
        assert price["range_from_net"] is None
        assert price["range_to_net"] is None


# ── Include=attributes value assertions ──────────────────────────────


class TestAttributeValues:
    """Attribute fields must match fixture values — not just count."""

    def _get_attrs(self, api):
        return _get_product(api, "&include=attributes")["attributes"]

    def _find_attr(self, attrs, feature_idx):
        matches = [a for a in attrs if a["feature_idx"] == feature_idx]
        assert len(matches) == 1, f"Expected 1 attr with feature_idx={feature_idx}, found {len(matches)}"
        return matches[0]

    def test_color_value_and_extension(self, api, simple_product, channel_full):
        attrs = self._get_attrs(api)
        color = self._find_attr(attrs, "color")
        assert color["value"] == "Red"
        assert color["value_idx"] == "red"
        assert color["feature_name"] == "Color"
        assert color["feature_type"] == "SELECT"
        assert color["extension"]["color_hash"] == "#CC0000"

    def test_weight_value(self, api, simple_product, channel_full):
        attrs = self._get_attrs(api)
        weight = self._find_attr(attrs, "weight")
        assert weight["value"] == "5.5"
        assert weight["feature_type"] == "DECIMAL"
        assert weight["feature_name"] == "Weight"

    def test_bool_attribute_value_translated_and_idx(self, api, simple_product, channel_full):
        attrs = self._get_attrs(api)
        handmade = self._find_attr(attrs, "is_handmade")
        assert handmade["value"] == "Yes"  # translated from "True"
        assert handmade["value_idx"] == "true"  # machine-readable
        assert handmade["feature_name"] == "Handmade"
        assert "label" not in handmade  # removed — value is the display text

    def test_attribute_flags_correct(self, api, simple_product, channel_full):
        attrs = self._get_attrs(api)
        color = self._find_attr(attrs, "color")
        assert color["is_visible"] is True
        assert color["has_visual_asset"] is True
        assert color["is_comparable"] is True

        weight = self._find_attr(attrs, "weight")
        assert weight["is_visible"] is True
        assert weight["has_visual_asset"] is False
        assert weight["is_comparable"] is False

    def test_seo_attribute_excluded_from_attributes_include(self, api, simple_product, channel_full):
        """meta_kw (is_seo=True, is_visible=False) must NOT appear in include=attributes."""
        attrs = self._get_attrs(api)
        meta_kw_matches = [a for a in attrs if a["feature_idx"] == "meta_kw"]
        assert len(meta_kw_matches) == 0, "SEO-only attribute should not be in include=attributes"

    def test_seo_attribute_present_in_full_seo(self, api, simple_product, channel_full):
        """meta_kw MUST appear in seo_attributes when include=full."""
        product = _get_product(api, "&include=full")
        seo_attrs = product["seo_attributes"]
        assert len(seo_attrs) >= 1, "seo_attributes should contain meta_kw"
        assert seo_attrs[0]["feature_idx"] == "meta_kw"

    def test_attribute_group_values_when_configured(self, api, simple_product, channel_full):
        """Color has group configured — exact values from fixture."""
        attrs = self._get_attrs(api)
        color = self._find_attr(attrs, "color")
        assert color["group_idx"] == "appearance"
        assert color["group_name"] == "Appearance"
        assert color["group_position"] == 10

    def test_attribute_group_null_when_not_configured(self, api, simple_product, channel_full):
        """Weight has no group — all group fields are null."""
        attrs = self._get_attrs(api)
        weight = self._find_attr(attrs, "weight")
        assert weight["group_idx"] is None
        assert weight["group_name"] is None
        assert weight["group_position"] is None

    def test_all_attributes_have_group_fields(self, api, simple_product, channel_full):
        """Every attribute in response has group_idx, group_name, group_position."""
        attrs = self._get_attrs(api)
        for attr in attrs:
            assert "group_idx" in attr, f"Missing group_idx on {attr['feature_idx']}"
            assert "group_name" in attr, f"Missing group_name on {attr['feature_idx']}"
            assert "group_position" in attr, f"Missing group_position on {attr['feature_idx']}"


# ── Include=full content value assertions ────────────────────────────


class TestFullIncludeContentValues:
    """Content fields in include=full must match fixture T9N values exactly."""

    def test_description_exact_html(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert product["description"] == "<p>Description</p>"

    def test_short_description_exact(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert product["short_description"] == "Short desc"

    def test_meta_title_exact(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert product["meta_title"] == "Test Chair | Store"

    def test_meta_description_exact(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert product["meta_description"] == "Meta desc"

    def test_url_keys_all_languages(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        url_keys = product["url_keys"]
        assert isinstance(url_keys, dict)
        assert url_keys.get("en") == "test-chair"
        assert url_keys.get("pl") == "testowe-krzeslo"

    def test_media_is_list(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert isinstance(product["media"], list)

    def test_children_skus_empty_for_simple(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert isinstance(product["children_skus"], list)
        assert product["children_skus"] == []


# ── Configurable product data validation ─────────────────────────────


class TestConfigurableDataValidation:
    """Configurable product: range pricing, children, parent_sku on children."""

    def test_configurable_range_pricing(self, api, configurable_product, channel_full):
        response = api.get(f"{BASE}{QS}&product_type=CONFIGURABLE")
        assert response.status_code == 200
        results = response.json()["results"]
        cfg = [r for r in results if r["sku"] == "V2-CFG-001"]
        assert len(cfg) == 1
        price = cfg[0]["price"]
        assert price["is_range"] is True
        assert price["range_from_gross"] == "500.00"
        assert price["range_to_gross"] == "1200.00"
        assert price["range_from_net"] == "406.50"
        assert price["range_to_net"] == "975.61"
        assert price["gross"] is None

    def test_configurable_children_skus_in_full(self, api, configurable_product, channel_full):
        response = api.get(f"{BASE}{QS}&url_key=config-sofa&include=full")
        assert response.status_code == 200
        product = response.json()["results"][0]
        children = sorted(product["children_skus"])
        assert children == ["V2-CFG-001-L", "V2-CFG-001-S"]

    def test_child_has_parent_sku(self, api, configurable_product, channel_full):
        response = api.get(f"{BASE}{QS}&sku=V2-CFG-001-S")
        assert response.status_code == 200
        child = response.json()["results"][0]
        assert child["parent_sku"] == "V2-CFG-001"
        assert child["url_key"] == "config-sofa-s"

    def test_configurable_url_key(self, api, configurable_product, channel_full):
        response = api.get(f"{BASE}{QS}&url_key=config-sofa")
        assert response.status_code == 200
        product = response.json()["results"][0]
        assert product["url_key"] == "config-sofa"
        assert product["product_type"] == "CONFIGURABLE"


# ── Review data validation ───────────────────────────────────────────


class TestReviewDataValidation:
    """review_rating must be decimal string, review_count must be int."""

    def test_review_rating_is_decimal_string(self, api, product_with_reviews, channel_full):
        response = api.get(f"{BASE}{QS}&sku=V2-REVIEW-001")
        assert response.status_code == 200
        product = response.json()["results"][0]
        assert product["review_rating"] == "4.50", f"Expected '4.50', got {product['review_rating']!r}"
        assert isinstance(product["review_rating"], str)

    def test_review_count_is_int(self, api, product_with_reviews, channel_full):
        response = api.get(f"{BASE}{QS}&sku=V2-REVIEW-001")
        assert response.status_code == 200
        product = response.json()["results"][0]
        assert product["review_count"] == 12
        assert isinstance(product["review_count"], int)
