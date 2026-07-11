# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Worker v2 fields — verify v2 columns on models have correct types and values.

Tests DB-level data integrity, not HTTP endpoints. Validates that:
- v2 columns (gross, net, percent_off, etc.) store correct types
- v1 and v2 columns coexist on the same row
- Attribute flags are booleans with correct defaults
- JSON fields (main_image, categories_data) store and retrieve correctly
"""

from decimal import Decimal

from django_matrix.models import Attribute, ProductPrice, ProductRepresentation


class TestPriceV2Columns:
    """ProductPrice v2 columns: gross/net/final/special/percent_off/range."""

    def test_gross_net_stored_as_decimal(self, simple_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.gross == Decimal("100.00")
        assert pp.net == Decimal("81.30")

    def test_final_gross_net_stored(self, simple_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.final_gross == Decimal("80.00")
        assert pp.final_net == Decimal("65.04")

    def test_special_gross_net_stored(self, simple_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.special_gross == Decimal("80.00")
        assert pp.special_net == Decimal("65.04")

    def test_percent_off_is_integer(self, simple_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.percent_off == 20
        assert isinstance(pp.percent_off, int)

    def test_v1_price_field_unchanged(self, simple_product, channel_full):
        """v1 column 'price' still correct alongside v2 'gross'."""
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.price == Decimal("100.00")

    def test_v1_final_price_unchanged(self, simple_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.final_price == Decimal("80.00")

    def test_dual_write_both_populated(self, simple_product, channel_full):
        """Same row has both v1 (price) and v2 (gross) non-null."""
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.price is not None
        assert pp.gross is not None

    def test_range_fields_on_configurable(self, configurable_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=configurable_product).first()
        assert pp.is_range is True
        assert pp.range_from == Decimal("500.00")
        assert pp.range_to == Decimal("1200.00")
        assert pp.range_from_net == Decimal("406.50")
        assert pp.range_to_net == Decimal("975.61")

    def test_range_fields_null_for_simple(self, simple_product, channel_full):
        pp = ProductPrice.objects.filter(product_representation=simple_product).first()
        assert pp.range_from_net is None
        assert pp.range_to_net is None


class TestProductV2Columns:
    """ProductRepresentation v2 columns: is_virtual, main_image, categories_data."""

    def test_is_virtual_false_for_physical(self, simple_product):
        assert simple_product.is_virtual is False

    def test_is_virtual_boolean_type(self, simple_product):
        assert isinstance(simple_product.is_virtual, bool)

    def test_main_image_set_from_fixture(self, simple_product):
        """Fixture sets main_image with source_set and alt_text."""
        assert simple_product.main_image is not None
        assert "source_set" in simple_product.main_image
        assert simple_product.main_image["alt_text"] == "Test Chair front view"

    def test_categories_data_is_list(self, simple_product):
        assert isinstance(simple_product.categories_data, list)

    def test_categories_data_structure(self, simple_product):
        cat = simple_product.categories_data[0]
        assert cat["idx"] == "chairs"
        assert cat["name"] == "Chairs"
        assert cat["url_key"] == "chairs"

    def test_main_image_stores_json(self, channel_full):
        """main_image JSONField stores and retrieves dict correctly."""
        ch = channel_full[0]
        img = {"source_set": [{"source": "/test.jpg", "width": 100}], "alt_text": "test"}
        pr = ProductRepresentation.objects.create(
            sku="V2-IMG-001",
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
            main_image=img,
        )
        pr.refresh_from_db()
        assert pr.main_image["alt_text"] == "test"
        assert pr.main_image["source_set"][0]["source"] == "/test.jpg"


class TestAttributeV2Flags:
    """Attribute v2 flag columns: is_visible, has_visual_asset, is_comparable, is_seo."""

    def test_flags_stored_correctly(self, simple_product, channel_full):
        color = Attribute.objects.get(product=simple_product, feature_idx="color")
        assert color.is_visible is True
        assert color.has_visual_asset is True
        assert color.is_comparable is True
        assert color.is_seo is False

    def test_seo_only_attribute(self, simple_product, channel_full):
        meta_kw = Attribute.objects.get(product=simple_product, feature_idx="meta_kw")
        assert meta_kw.is_visible is False
        assert meta_kw.has_visual_asset is False
        assert meta_kw.is_seo is True

    def test_bool_attribute_flags(self, simple_product, channel_full):
        handmade = Attribute.objects.get(product=simple_product, feature_idx="is_handmade")
        assert handmade.is_visible is True
        assert handmade.has_visual_asset is False
        assert handmade.is_comparable is False
        assert handmade.is_seo is False

    def test_default_flag_values(self, channel_full):
        """New attribute without explicit flags gets defaults."""
        ch = channel_full[0]
        pr = ProductRepresentation.objects.create(
            sku="V2-FLAG-001",
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
        )
        attr = Attribute.objects.create(
            product=pr,
            hash="flagtest",
            feature_idx="test",
            feature_type="VARCHAR255",
        )
        assert attr.is_visible is True  # default
        assert attr.has_visual_asset is False  # default
        assert attr.is_comparable is False  # default
        assert attr.is_seo is False  # default


class TestAttributeGroupColumns:
    """Attribute group columns: group_idx, group_name_t9n, group_position."""

    def test_group_fields_stored(self, simple_product, channel_full):
        attr = Attribute.objects.get(product=simple_product, feature_idx="color")
        assert attr.group_idx == "appearance"
        assert attr.group_name_t9n == {"en": "Appearance", "pl": "Wygląd"}
        assert attr.group_position == 10

    def test_group_fields_null_when_no_group(self, simple_product, channel_full):
        attr = Attribute.objects.get(product=simple_product, feature_idx="weight")
        assert attr.group_idx is None
        assert attr.group_name_t9n is None
        assert attr.group_position is None

    def test_group_default_values_on_new_attribute(self, channel_full):
        ch = channel_full[0]
        pr = ProductRepresentation.objects.create(
            sku="V2-GRP-001",
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
        )
        attr = Attribute.objects.create(
            product=pr,
            hash="grptest",
            feature_idx="test",
            feature_type="VARCHAR255",
        )
        assert attr.group_idx is None
        assert attr.group_name_t9n is None
        assert attr.group_position is None
