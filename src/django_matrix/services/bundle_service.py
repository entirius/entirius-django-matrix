# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import ROUND_UP, Decimal

from django_pim.services.bundle_data import get_default_subproducts

try:
    from django_pricemanager.output_bundle import get_aggregated_bundle_price
except ImportError:  # pricemanager is an optional extra; the fill worker gates on _HAS_PRICEMANAGER
    get_aggregated_bundle_price = None

from django_matrix import settings


def get_default_selected_skus(
    bundle_sku: str,
    links_map: dict[str, dict[str, dict]],
    limits_map: dict[str, dict],
) -> set[str] | None:
    """Matrix-side gate around PIM's pure default-selection rule.

    Returns None when there is nothing to filter by — either a legacy bundle
    (no min/max limit configured) or a ranged bundle where no subproduct is
    required/default. Callers MUST treat None as "no filtering": an empty
    selection means the customer picks freely, not that the bundle has no
    priceable components.

    Returns the non-empty set of default SKUs for ranged bundles.
    """
    limits = limits_map.get(bundle_sku, {})
    if "min" not in limits and "max" not in limits:
        return None
    sub_items = links_map.get(bundle_sku, {})
    return set(get_default_subproducts(sub_items).keys()) or None


def aggregate_ranged_bundle_for_read_model(
    channel_idx: str,
    country_code: str,
    currency_code: str,
    bundle_sku: str,
    default_skus: set[str],
    links: dict[str, dict],
) -> dict | None:
    """Thin wrapper: ask pricemanager to aggregate the given default subproducts,
    then translate the gross/net snapshot into ProductPrice field shape per
    matrix's PRICE_TYPE setting.

    Returns None if any default subproduct lacks a price in the active pricelist.
    Returned dict keys map directly onto ProductPrice fields.
    """
    if not default_skus:
        return None
    try:
        components_quantities = {sku: links[sku]["quantity"] for sku in default_skus}
    except KeyError:
        return None

    snapshot, _verified_only = get_aggregated_bundle_price(
        channel_idx=channel_idx,
        country_code=country_code,
        currency_code=currency_code,
        bundle_sku=bundle_sku,
        components_quantities=components_quantities,
    )
    if snapshot is None:
        return None
    return _snapshot_to_product_price_fields(snapshot)


def _snapshot_to_product_price_fields(snapshot: dict) -> dict:
    quantum = Decimal(settings.PRICE_DECIMAL_PLACES)

    if settings.PRICE_TYPE == "NET":
        primary = snapshot["net"]
        opposite = snapshot["gross"]
        primary_final = snapshot["final_net"]
        primary_special = snapshot["special_net"]
        opposite_special = snapshot["special_gross"]
    else:  # GROSS (default)
        primary = snapshot["gross"]
        opposite = snapshot["net"]
        primary_final = snapshot["final_gross"]
        primary_special = snapshot["special_gross"]
        opposite_special = snapshot["special_net"]

    tax_rate = snapshot.get("tax_rate")
    if tax_rate is not None:
        tax_amount = Decimal(tax_rate).quantize(quantum, rounding=ROUND_UP)
        tax_rule = f"{round(tax_rate * 100)}%"
    else:
        tax_amount = None
        tax_rule = None

    def q(value):
        return Decimal(value).quantize(quantum, rounding=ROUND_UP) if value is not None else None

    return {
        "price": q(primary),
        "final_price": q(primary_final),
        "special_price": q(primary_special),
        "has_special_price": snapshot["has_special_price"],
        "promo_badge": snapshot["promo_badge"],
        "tax_amount": tax_amount,
        "tax_rule": tax_rule,
        "price_tax_config_opposite": q(opposite),
        "special_price_tax_config_opposite": q(opposite_special),
        "special_from_date": snapshot["special_from_date"],
        "special_to_date": snapshot["special_to_date"],
    }
