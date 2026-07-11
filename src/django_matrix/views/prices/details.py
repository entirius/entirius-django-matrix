# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import (
    api_view,
    authenticate_optional,
    parse_parameters,
    require_http_method,
)
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.price import price_collection
from django_matrix.repository.raw_sql.prices import (
    ProductPrice as ProductPricesRepository,
)
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import (
    PriceDetailsQuery,
    get_view_variable_from_kwargs,
    params_factory_for_price_details,
)


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(PriceDetailsQuery.Schema())
@prepare_view
def prices_details_view(request, params: PriceDetailsQuery, url_key: str, *args, **kwargs) -> "Response":
    """Returns product price"""

    param = params_factory_for_price_details(params=params, url_key=[url_key])

    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    customer = (
        request.user.customer if request.user is not None and getattr(request.user, "is_customer", False) else None
    )
    is_customer_verified = (
        customer.is_verified if customer is not None and hasattr(request.user.customer, "is_verified") else False
    )
    prices_result, query_msg = ProductPricesRepository().find_by_api_query(
        params=param,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=is_customer_verified,
    )
    price, collection_msg = price_collection(
        prices_result, channel=channel, country=country, currency=currency, asdict=True, customer=customer
    )
    if collection_msg:
        messages += collection_msg

    if len(price) == 0:
        raise NotFound(f"Price {url_key} does not exist")
    elif len(price) > 1:
        prices = price[0]
        messages.append("Result query responded with more that one price. Use Listing with this url_key to check.")
    else:
        prices = price[0]

    messages += query_msg

    return Response(prices, messages=messages)
