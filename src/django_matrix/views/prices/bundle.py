# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_pim.services.bundle_data import get_bundle_limits, get_bundle_subproducts
from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.price import price_collection
from django_matrix.repository.orm.prices import Prices as ProductPricesRepository
from django_matrix.services.bundle_service import get_default_selected_skus
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import BundleQuery, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(BundleQuery.Schema())
@prepare_view
def prices_bundle_view(request, params: BundleQuery, *args, **kwargs) -> "Response":
    """Returns list of prices"""

    # These variables are prepared by prepare_view decorator. Don't mess with this
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
    bundle_limits = get_bundle_limits(channel.idx, bundle_skus)
    bundle_links = get_bundle_subproducts(channel.idx, bundle_skus)

    prices_repository = ProductPricesRepository(channel)
    price_result = []
    for sku in bundle_skus:
        price, msg = prices_repository.get_product_bundle_components_price(
            country_code=country.iso2,
            currency_code=currency.iso3,
            bundle_sku=sku,
            uid=None,  # Cały matrix nie umie w ceny customera wiec tutaj tez tak zostawiamy mimo ze jest mozliwosc
            is_customer_verified=is_customer_verified,
        )
        messages += [msg]

        # Bundles with min/max limit configured return only the default-selected
        # subproducts (is_required OR is_default) so the storefront's sum matches
        # what actually goes into the cart. Legacy bundles (no limits): unchanged.
        active_skus = get_default_selected_skus(sku, bundle_links, bundle_limits)
        if active_skus is not None:
            price = [p for p in price if p["sku"] in active_skus]

        price_result += price

    prices, collection_msg = price_collection(
        price_result, asdict=True, channel=channel, country=country, currency=currency, customer=customer
    )
    if collection_msg:
        messages += collection_msg

    return Response(prices, messages=messages)
