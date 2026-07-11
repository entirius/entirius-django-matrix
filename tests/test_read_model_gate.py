# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Read model gate tests — attributes without front-facing flags are skipped."""

import pytest

from django_matrix.models import Attribute, Channel, ProductRepresentation


@pytest.fixture
def channel_basic(db):
    return Channel.objects.create(
        idx="gate-test", label="Gate Test", default_order="sku", default_order_direction="ASC"
    )


@pytest.fixture
def product(channel_basic):
    return ProductRepresentation.objects.create(
        sku="GATE-001", channel=channel_basic, product_type="SIMPLE", kind_of_product="PHYSICAL"
    )


class TestReadModelGate:
    """Worker skips attributes without any front-facing flag.

    FRONT_FACING = is_visible OR has_visual_asset OR is_comparable OR is_seo
    """

    def test_visible_attribute_written(self, product):
        Attribute.objects.create(
            product=product,
            hash="vis1",
            feature_idx="color",
            feature_type="SELECT",
            is_visible=True,
            has_visual_asset=False,
            is_comparable=False,
            is_seo=False,
        )
        assert Attribute.objects.filter(product=product, is_visible=True).count() == 1

    def test_visual_asset_attribute_written(self, product):
        Attribute.objects.create(
            product=product,
            hash="vis2",
            feature_idx="color2",
            feature_type="SELECT",
            is_visible=False,
            has_visual_asset=True,
            is_comparable=False,
            is_seo=False,
        )
        assert Attribute.objects.filter(product=product, has_visual_asset=True).count() == 1

    def test_comparable_attribute_written(self, product):
        Attribute.objects.create(
            product=product,
            hash="cmp1",
            feature_idx="weight",
            feature_type="DECIMAL",
            is_visible=False,
            has_visual_asset=False,
            is_comparable=True,
            is_seo=False,
        )
        assert Attribute.objects.filter(product=product, is_comparable=True).count() == 1

    def test_seo_attribute_written(self, product):
        Attribute.objects.create(
            product=product,
            hash="seo1",
            feature_idx="meta_kw",
            feature_type="TEXT",
            is_visible=False,
            has_visual_asset=False,
            is_comparable=False,
            is_seo=True,
        )
        assert Attribute.objects.filter(product=product, is_seo=True).count() == 1

    def test_mixed_flags_written(self, product):
        """Attribute with is_visible=false but has_visual_asset=true should be written."""
        Attribute.objects.create(
            product=product,
            hash="mix1",
            feature_idx="material",
            feature_type="SELECT",
            is_visible=False,
            has_visual_asset=True,
            is_comparable=True,
            is_seo=False,
        )
        assert Attribute.objects.filter(product=product, feature_idx="material").exists()

    def test_partial_index_visible(self, product):
        """Partial index on is_visible=true works for filtering."""
        Attribute.objects.create(product=product, hash="a1", feature_idx="f1", feature_type="SELECT", is_visible=True)
        Attribute.objects.create(
            product=product, hash="a2", feature_idx="f2", feature_type="SELECT", is_visible=False, has_visual_asset=True
        )
        Attribute.objects.create(
            product=product, hash="a3", feature_idx="f3", feature_type="SELECT", is_visible=True, has_visual_asset=True
        )

        visible = Attribute.objects.filter(product=product, is_visible=True)
        visual = Attribute.objects.filter(product=product, has_visual_asset=True)

        assert visible.count() == 2  # f1, f3
        assert visual.count() == 2  # f2, f3
