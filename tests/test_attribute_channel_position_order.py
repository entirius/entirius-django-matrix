# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Attribute ordering — global display_order by default, per-channel position behind the flag.

``MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION`` is imported by name into
``repository/raw_sql/attribute.py``, so the tests patch the constant on that module — patching
``django_matrix.settings`` would not reach the name the query builder already bound.
"""

import pytest

from django_matrix.repository.raw_sql import attribute as attribute_module
from django_matrix.utils.params import AttributeQuery

SKU = "ENT-KESTREL-001"


@pytest.fixture
def conflicting_attribute_order(channel_full):
    """Two visible attributes whose global order and per-channel order disagree.

    display_order says finish (10) before capacity (20); the channel position says
    capacity (10) before finish (20).
    """
    from django_pim.models import Feature, FeatureScopeEnum, FeatureTypeEnum

    from django_matrix.models import Attribute, ProductRepresentation, VisibilityFeatures

    ch, lang, currency, country = channel_full
    product = ProductRepresentation.objects.create(
        sku=SKU,
        channel=ch,
        product_type="SIMPLE",
        kind_of_product="PHYSICAL",
        on_stock=True,
    )
    for idx, name, display_order, position in (("finish", "Finish", 10, 20), ("capacity", "Capacity", 20, 10)):
        feature = Feature.objects.create(
            idx=idx,
            name_t9n={"en": name},
            feature_type=FeatureTypeEnum.SELECT,
            scope=FeatureScopeEnum.BUSINESS_UNIT,
            display_order=display_order,
        )
        VisibilityFeatures.objects.create(channel=ch, feature=feature, position=position)
        Attribute.objects.create(
            product=product,
            hash=f"hash-{idx}",
            feature_idx=idx,
            feature_type="SELECT",
            feature_name_t9n={"en": name},
            attribute_idx=f"{idx}-value",
            attribute_value_text=name,
            is_visible=True,
        )
    return ch, lang


def _feature_idx_order(channel, language, only_custom: bool = False) -> list[str]:
    attributes, _messages = attribute_module.Attribute().find_by_api_query(
        params=AttributeQuery(sku=[SKU], only_custom=only_custom), channel=channel, language=language
    )
    return [attribute["feature_idx"] for attribute in attributes]


def test_default_orders_by_global_display_order(conflicting_attribute_order):
    channel, language = conflicting_attribute_order
    assert _feature_idx_order(channel, language) == ["finish", "capacity"]


def test_flag_orders_by_channel_position(conflicting_attribute_order, monkeypatch):
    monkeypatch.setattr(attribute_module, "MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION", True)
    channel, language = conflicting_attribute_order
    assert _feature_idx_order(channel, language) == ["capacity", "finish"]


@pytest.fixture
def attribute_without_channel_position(channel_full):
    """Two customization attributes, only one of them listed in the per-channel table.

    ``only_custom`` skips the visibility gate, so ``engraving`` is returned even though it has
    no ``VisibilityFeatures`` row and therefore no position. Global order says engraving (10)
    before finish (20); the channel position says finish (10) before the positionless engraving.
    """
    from django_pim.models import Feature, FeatureScopeEnum, FeatureTypeEnum

    from django_matrix.models import Attribute, ProductRepresentation, VisibilityFeatures

    ch, lang, currency, country = channel_full
    product = ProductRepresentation.objects.create(
        sku=SKU,
        channel=ch,
        product_type="SIMPLE",
        kind_of_product="PHYSICAL",
        on_stock=True,
    )
    for idx, name, display_order, position in (("finish", "Finish", 20, 10), ("engraving", "Engraving", 10, None)):
        feature = Feature.objects.create(
            idx=idx,
            name_t9n={"en": name},
            feature_type=FeatureTypeEnum.SELECT,
            scope=FeatureScopeEnum.BUSINESS_UNIT,
            display_order=display_order,
        )
        if position is not None:
            VisibilityFeatures.objects.create(channel=ch, feature=feature, position=position)
        Attribute.objects.create(
            product=product,
            hash=f"hash-{idx}",
            feature_idx=idx,
            feature_type="SELECT",
            feature_name_t9n={"en": name},
            attribute_idx=f"{idx}-value",
            attribute_value_text=name,
            is_visible=True,
            feature_is_for_customization=True,
        )
    return ch, lang


def test_flag_sorts_attributes_without_channel_position_last(attribute_without_channel_position, monkeypatch):
    monkeypatch.setattr(attribute_module, "MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION", True)
    channel, language = attribute_without_channel_position
    assert _feature_idx_order(channel, language, only_custom=True) == ["finish", "engraving"]
