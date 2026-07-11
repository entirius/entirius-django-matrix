# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.attribute import attribute_collection
from django_matrix.dto.view.product import product_collection
from django_matrix.repository.raw_sql.attribute import Attribute as AttributeRepository
from django_matrix.repository.raw_sql.product import Product as ProductRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import (
    AttributeQuery,
    DetailsQuery,
    get_view_variable_from_kwargs,
    params_factory_for_details,
)


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(DetailsQuery.Schema())
@prepare_view
def products_details_view(request, params: DetailsQuery, url_key: str, *args, **kwargs) -> "Response":
    """Returns a paginated response with a list of products"""
    param = params_factory_for_details(params=params, url_key=[url_key])
    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)

    is_customer_verified = False
    if request.user is not None and getattr(request.user, "customer", False):
        if hasattr(request.user.customer, "is_verified"):
            is_customer_verified = request.user.customer.is_verified

    products_result, count_pages, query_msg, *_ = ProductRepository().find_by_api_query(
        params=param,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=is_customer_verified,
        limit_offset=False,
    )
    products, sku_list = product_collection(
        products_result, asdict=True, get_sku_list=True, is_customer_verified=is_customer_verified
    )

    if not is_customer_verified:
        messages.append("Your are not verified customer and price query may be limited")

    # Attributes
    if params.fetch_attributes is True and len(sku_list) > 0:
        attr_params = AttributeQuery(sku=sku_list)
        attributes_result, attr_msg = AttributeRepository().find_by_api_query(
            params=attr_params, channel=channel, language=language
        )

        messages += attr_msg

        attributes = attribute_collection(attributes_result, asdict=True, language_iso2=language.iso2)

        for product in products:
            if product["sku"] in attributes:
                product["attributes"] = attributes[product["sku"]]

    if len(products) == 0:
        raise NotFound(f"Product {url_key} does not exist")
    elif len(products) > 1:
        product = products[0]
        messages.append("Result query responded with more that one product. Use Listing with this url_key to check.")
    else:
        product = products[0]

    messages += query_msg

    return Response(product, messages=messages)
