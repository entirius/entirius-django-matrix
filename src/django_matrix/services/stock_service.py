# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stock service — wraps checkout/QMS soft dependency for real-time stock."""


def get_stock_for_skus(skus: list[str], channel_idx: str) -> dict[str, dict]:
    """Returns {sku: {quantity, is_in_stock}} for given SKUs. Empty dict if no stock module."""
    quantities = get_quantities(skus, channel_idx)
    result = {}
    for sku in skus:
        qty = quantities.get(sku, 0)
        result[sku] = {"quantity": qty, "is_in_stock": qty > 0}
    return result


def get_quantities(skus: list[str], channel_idx: str) -> dict[str, int]:
    """Saleable quantity per SKU as the cart counts it, so a SKU reported in stock is one the cart accepts: a
    bundle by what its components allow, not by its own Stock row. SKUs without data are left out."""
    quantities = _get_quantities(skus, channel_idx)
    quantities.update(_get_bundle_quantities(skus, channel_idx))
    return quantities


def _get_quantities(skus: list[str], channel_idx: str) -> dict[str, int]:
    """Try checkout Stock first (its global supplier, as the cart reads it), then QMS. Return empty if neither
    available."""
    # RuntimeError: an app that is installed but not in INSTALLED_APPS raises it on model import, not ImportError.
    try:
        from django_checkout.models import Stock

        quantities = {}
        stock_data = Stock.annotated.filter(
            product__sku__in=skus,
            product__channel__idx=channel_idx,
            supplier__channel__idx=channel_idx,
            supplier__is_global=True,
        ).values("product__sku", "saleable_quantity")
        for row in stock_data:
            quantities[row["product__sku"]] = row["saleable_quantity"]
        return quantities
    except (ImportError, RuntimeError):
        pass

    try:
        from django_qms.output import get_quantities

        return dict(get_quantities(channel_idx).filter(product__sku__in=skus))
    except (ImportError, RuntimeError):
        pass

    return {}


def _get_bundle_quantities(skus: list[str], channel_idx: str) -> dict[str, int]:
    """The bundles among `skus`, counted by checkout from their components. Empty without checkout, or with a
    checkout that has no `output.quantities.get_bundle_quantities` yet: bundles then keep their own Stock row."""
    try:
        from django_checkout.output.quantities import get_bundle_quantities
    except (ImportError, RuntimeError):
        return {}
    return get_bundle_quantities(skus, channel_idx)
