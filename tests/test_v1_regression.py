# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v1 regression tests — verify v1 endpoints return same shape after v2 migration.

These tests ensure backward compatibility: v1 views don't break when v2 columns
are added to models. v1 raw SQL queries don't SELECT v2 columns.
"""

import pytest

from django_matrix.models import ProductPrice, ProductRepresentation


@pytest.fixture
def product_with_v2_columns(channel_full):
    """Product that has both v1 and v2 columns populated."""
    ch, lang, currency, country = channel_full
    pr = ProductRepresentation.objects.create(
        sku="TEST-V1-001",
        channel=ch,
        product_type="SIMPLE",
        kind_of_product="PHYSICAL",
        on_stock=True,
        # v2 columns
        is_virtual=False,
        main_image={"source_set": [{"source": "/test.jpg", "width": 100, "height": 100}], "alt_text": "test"},
        categories_data=[{"idx": "chairs", "name": "Chairs", "url_key": "chairs"}],
    )
    return pr


class TestV1ProductRepresentationUnchanged:
    """v1 fields on ProductRepresentation are not affected by v2 columns."""

    def test_v1_fields_still_accessible(self, product_with_v2_columns):
        pr = product_with_v2_columns
        assert pr.sku == "TEST-V1-001"
        assert pr.product_type == "SIMPLE"
        assert pr.kind_of_product == "PHYSICAL"
        assert pr.on_stock is True

    def test_v2_columns_coexist(self, product_with_v2_columns):
        pr = product_with_v2_columns
        assert pr.is_virtual is False
        assert pr.main_image is not None
        assert pr.categories_data is not None

    def test_v1_query_does_not_break(self, product_with_v2_columns):
        """v1 raw SQL selects specific columns — new columns don't interfere."""
        pr = (
            ProductRepresentation.objects.filter(sku="TEST-V1-001")
            .values("sku", "product_type", "kind_of_product", "on_stock")
            .first()
        )
        assert pr["sku"] == "TEST-V1-001"
        assert pr["kind_of_product"] == "PHYSICAL"


class TestV1AttributeUnchanged:
    """v1 Attribute fields not affected by v2 flag columns."""

    def test_attribute_with_v2_flags(self, product_with_v2_columns):
        from django_matrix.models import Attribute

        attr = Attribute.objects.create(
            product=product_with_v2_columns,
            hash="test123hash",
            feature_idx="color",
            feature_name_t9n={"en": "Color"},
            feature_type="SELECT",
            attribute_idx="red",
            attribute_value_text="Red",
            # v2 flags
            is_visible=True,
            has_visual_asset=True,
            is_comparable=False,
            is_seo=False,
        )
        # v1 fields intact
        assert attr.feature_idx == "color"
        assert attr.attribute_value_text == "Red"
        # v2 flags coexist
        assert attr.is_visible is True
        assert attr.has_visual_asset is True


class TestV1ProductPriceUnchanged:
    """v1 price fields not affected by v2 gross/net columns."""

    def test_price_with_v2_columns(self, product_with_v2_columns, channel_full):
        ch = channel_full[0]
        pp = ProductPrice.objects.create(
            product_representation=product_with_v2_columns,
            currency=ch.default_currency,
            country=ch.default_country,
            price=100.00,
            final_price=80.00,
            has_special_price=True,
            special_price=80.00,
            tax_amount=0.23,
            tax_rule="23%",
            promo_badge="20%",
            # v2 columns
            gross=100.00,
            net=81.30,
            final_gross=80.00,
            final_net=65.04,
            special_gross=80.00,
            special_net=65.04,
            percent_off=20,
        )
        # v1 fields intact
        assert pp.price == 100.00
        assert pp.final_price == 80.00
        assert pp.promo_badge == "20%"
        # v2 fields coexist
        assert pp.gross == 100.00
        assert pp.net == 81.30
        assert pp.percent_off == 20
