# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import Decimal
from types import SimpleNamespace

from django_matrix.workers.fill_read_model_prices import _set_v2_range_fields


def _range(special_from, regular_from):
    return SimpleNamespace(
        is_range=True,
        range_from=regular_from,
        special_price_range_from=special_from,
        price_tax_config_opposite_from=None,
        price_tax_config_opposite_to=None,
        special_price_tax_config_opposite_from=None,
        special_price_tax_config_opposite_to=None,
    )


def test_a_range_whose_cheapest_special_price_is_above_its_cheapest_price_has_no_discount():
    """The cheapest special price (1299) is of another variant than the cheapest price (549)."""
    price = _range(Decimal("1299.00"), Decimal("549.00"))
    _set_v2_range_fields(price)
    assert price.percent_off is None


def test_a_range_with_a_real_discount_keeps_it():
    price = _range(Decimal("400.00"), Decimal("500.00"))
    _set_v2_range_fields(price)
    assert price.percent_off == 20
