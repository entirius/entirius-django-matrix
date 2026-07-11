# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.price import price_collection
from django_matrix.repository.orm.bundle import get_bundle_limits, get_bundle_links
from django_matrix.repository.orm.prices import Prices as ProductPricesRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import BundleQuery, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(BundleQuery.Schema())
@prepare_view
def bundle_config_view(request, params: BundleQuery, *args, **kwargs) -> "Response":
    """Returns bundle structure: sub-items with flags, limits and prices"""

    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    customer = (
        request.user.customer if request.user is not None and getattr(request.user, "is_customer", False) else None
    )
    is_customer_verified = (
        customer.is_verified if customer is not None and hasattr(request.user.customer, "is_verified") else False
    )

    if not params.sku:
        raise NotFound("Bundle sku is required")

    bundle_skus = params.sku
    prices_repository = ProductPricesRepository(channel)
    bundle_links = get_bundle_links(bundle_skus)
    bundle_limits = get_bundle_limits(bundle_skus)

    result = []
    for bundle_sku in bundle_skus:
        sub_items_meta = bundle_links.get(bundle_sku, {})
        limits = bundle_limits.get(bundle_sku, {})

        prices_raw, msg = prices_repository.get_product_bundle_components_price(
            country_code=country.iso2,
            currency_code=currency.iso3,
            bundle_sku=bundle_sku,
            uid=None,
            is_customer_verified=is_customer_verified,
        )
        if msg:
            messages.append(msg)

        prices_by_sku, collection_msg = price_collection(
            prices_raw, asdict=True, channel=channel, country=country, currency=currency, customer=customer
        )
        if collection_msg:
            messages += collection_msg

        prices_map = {p["sku"]: p for p in prices_by_sku}

        sub_items = [
            {
                "sku": sub_sku,
                "quantity": meta["quantity"],
                "is_required": meta["is_required"],
                "is_default": meta["is_default"],
                "can_change_quantity": meta["can_change_quantity"],
                "price": prices_map.get(sub_sku),
            }
            for sub_sku, meta in sub_items_meta.items()
        ]

        result.append(
            {
                "sku": bundle_sku,
                "max_limit": limits.get("max_limit"),
                "min_limit": limits.get("min_limit"),
                "sub_items": sub_items,
            }
        )

    return Response(result, messages=messages)
