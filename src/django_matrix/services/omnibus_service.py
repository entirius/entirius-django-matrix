# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Omnibus service — 30-day lowest price from django_omnibus (soft dependency)."""

from django_matrix.models import ProductPrice


def get_omnibus_prices(skus: list[str], channel, currency, country) -> dict[str, dict]:
    """Returns {sku: {currency, omnibus_gross, omnibus_net, status}}. Empty dict if no data."""
    currency_code = (
        currency.iso3 if currency else (channel.default_currency.iso3 if channel.default_currency else "EUR")
    )

    qs = ProductPrice.objects.filter(
        product_representation__sku__in=skus, product_representation__channel=channel, omnibus_price__isnull=False
    ).select_related("product_representation")

    if currency:
        qs = qs.filter(currency=currency)
    if country:
        qs = qs.filter(country=country)

    result = {}
    for pp in qs:
        sku = pp.product_representation.sku
        result[sku] = {
            "currency": currency_code,
            "omnibus_gross": str(pp.omnibus_price) if pp.omnibus_price else None,
            "omnibus_net": str(pp.price_tax_config_opposite) if pp.price_tax_config_opposite else None,
            "status": "normal_price",
        }
    return result
