# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stock service — wraps checkout/QMS soft dependency for real-time stock."""


def get_stock_for_skus(skus: list[str], channel_idx: str) -> dict[str, dict]:
    """Returns {sku: {quantity, is_in_stock}} for given SKUs. Empty dict if no stock module."""
    quantities = _get_quantities(skus, channel_idx)
    result = {}
    for sku in skus:
        qty = quantities.get(sku, 0)
        result[sku] = {"quantity": qty, "is_in_stock": qty > 0}
    return result


def _get_quantities(skus: list[str], channel_idx: str) -> dict[str, int]:
    """Try checkout Stock first, then QMS. Return empty if neither available."""
    try:
        from django_checkout.models import Stock

        quantities = {}
        stock_data = Stock.annotated.filter(product__sku__in=skus, product__channel__idx=channel_idx).values(
            "product__sku", "saleable_quantity"
        )
        for row in stock_data:
            quantities[row["product__sku"]] = row["saleable_quantity"]
        return quantities
    except ImportError:
        pass

    try:
        from django_qms.output import get_quantities

        return dict(get_quantities(channel_idx).filter(product__sku__in=skus))
    except ImportError:
        pass

    return {}
