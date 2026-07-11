# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import (
    api_view,
    authenticate_optional,
    parse_parameters,
    require_http_method,
)
from django_utils.api.exceptions import BadRequest
from django_utils.api.responses import Response

from django_matrix.dto.view.price import price_collection
from django_matrix.repository.raw_sql.prices import (
    ProductPrice as ProductPricesRepository,
)
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import PriceQuery, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(PriceQuery.Schema())
@prepare_view
def prices_listing_view(request, params: PriceQuery, *args, **kwargs) -> "Response":
    """Returns list of prices"""

    # Reject unbounded lookups — without sku/url_key this hits every product in
    # the channel and exhausts the uwsgi worker (HARAKIRI in production logs).
    if not params.sku and not params.url_key:
        raise BadRequest("Either 'sku' or 'url_key' query parameter is required.")

    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    customer = (
        request.user.customer if request.user is not None and getattr(request.user, "is_customer", False) else None
    )
    is_customer_verified = (
        customer.is_verified if customer is not None and hasattr(request.user.customer, "is_verified") else False
    )
    price_result, query_msg = ProductPricesRepository().find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=is_customer_verified,
    )
    prices, collection_msg = price_collection(
        price_result, asdict=True, channel=channel, country=country, currency=currency, customer=customer
    )
    if collection_msg:
        messages += collection_msg

    messages += query_msg

    return Response(prices, messages=messages)
