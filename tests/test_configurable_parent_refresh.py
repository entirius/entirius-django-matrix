# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A fill of one product leaves its configurable parent as a full fill of the channel would.

- a fill of one variant keeps the parent's price range over all variants, not the price of that variant
- a fill of the parent keeps the search text and filterable attributes of all its variants
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from django_matrix.models import ProductPrice, ProductRepresentation
from django_matrix.workers import fill_read_model_prices as prices_worker
from django_matrix.workers.fill_read_model_prices import fill_read_model_prices
from django_matrix.workers.fill_read_model_products_and_attributes import (
    fill_read_model_products_and_attributes,
)

PARENT_SKU = "CFG-PARENT"
VARIANT_PRICES = {
    "CFG-1": Decimal("549.00"),
    "CFG-2": Decimal("899.00"),
    "CFG-3": Decimal("1299.00"),
    "CFG-4": Decimal("1749.00"),
}


@pytest.fixture
def family(channel_full):
    """A configurable read-model row with four variants, each with its own search text."""
    ch = channel_full[0]
    parent = ProductRepresentation.objects.create(
        sku=PARENT_SKU, channel=ch, product_type="CONFIGURABLE", kind_of_product="PHYSICAL", search=["Parent set"]
    )
    for sku in VARIANT_PRICES:
        ProductRepresentation.objects.create(
            sku=sku,
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
            parent=parent,
            search=[f"text of {sku}"],
            attributes_filter={"color": [sku]},
        )
    return parent


@pytest.fixture
def pim_configurable(channel_full):
    """The enabled configurable PIM product behind the parent row, so a product fill rewrites it."""
    from django_pim.models import Channel as PimChannel
    from django_pim.models import FeatureSet, Product, RealProduct

    ch, lang, currency, _country = channel_full
    shop = PimChannel.objects.create(idx=ch.idx, name=ch.idx, default_language=lang, default_currency=currency)
    return Product.objects.create(
        product_class=2,
        real_product=RealProduct.objects.create(sku=PARENT_SKU),
        shop=shop,
        feature_set=FeatureSet.objects.create(idx="cfg"),
        is_enabled=True,
    )


def _price_row(sku: str, price: Decimal) -> SimpleNamespace:
    return SimpleNamespace(
        product=SimpleNamespace(sku=sku),
        tax_rate=None,
        net_value=price,
        gross_value=price,
        special_net_value=None,
        special_gross_value=None,
        special_from_date=None,
        special_to_date=None,
        is_egible_for_special_price=False,
    )


def _pricelist_rows(pricelist, sku=None):
    return [_price_row(s, p) for s, p in VARIANT_PRICES.items() if sku is None or s == sku]


def _fill_prices(channel, product_id=None):
    pricelist = SimpleNamespace(sale_channel=SimpleNamespace(is_only_for_verified_user=False))
    with (
        patch.object(prices_worker, "read_from_current", return_value=False),
        patch.object(prices_worker, "get_latest_pricelist", return_value=pricelist),
        patch.object(prices_worker, "get_price_qs_by_given_pricelist", side_effect=_pricelist_rows),
    ):
        fill_read_model_prices(channel=channel, product_id=product_id)


def _parent_price(parent) -> ProductPrice:
    return ProductPrice.objects.get(product_representation=parent)


def test_variant_fill_keeps_the_parent_price_range(channel_full, family):
    _fill_prices(channel_full[0])
    assert (_parent_price(family).range_from, _parent_price(family).range_to) == (Decimal("549.00"), Decimal("1749.00"))

    _fill_prices(channel_full[0], product_id="CFG-4")

    parent_price = _parent_price(family)
    assert parent_price.is_range is True
    assert (parent_price.range_from, parent_price.range_to) == (Decimal("549.00"), Decimal("1749.00"))
    assert parent_price.price is None


def test_variant_fill_creates_the_parent_price_from_all_variants(channel_full, family):
    _fill_prices(channel_full[0], product_id="CFG-4")

    parent_price = _parent_price(family)
    assert parent_price.is_range is True
    assert (parent_price.range_from, parent_price.range_to) == (Decimal("549.00"), Decimal("1749.00"))


def test_parent_fill_keeps_the_search_text_of_all_variants(channel_full, family, pim_configurable):
    fill_read_model_products_and_attributes(channel=channel_full[0], product_class=2, product_id=PARENT_SKU)

    family.refresh_from_db()
    assert set(family.search) == {f"text of {sku}" for sku in VARIANT_PRICES}
    assert sorted(family.attributes_filter["color"]) == sorted(VARIANT_PRICES)
