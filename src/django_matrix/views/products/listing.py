# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.responses import PaginatedResponse

from django_matrix.dto.view.product import product_collection
from django_matrix.repository.orm.product_variant_groups import ProductVariantGroups as ProductVariantGroupRepository
from django_matrix.repository.raw_sql.product import Product as ProductRepository
from django_matrix.services.attribute_service import fetch_and_attach_attributes
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import Query, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(Query.Schema())
@prepare_view
def products_listing_view(request, params: Query, *args, **kwargs) -> "PaginatedResponse":
    """Returns a paginated response with a list of products"""

    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    is_customer_verified = False
    if request.user is not None and getattr(request.user, "customer", False):
        if hasattr(request.user.customer, "is_verified"):
            is_customer_verified = request.user.customer.is_verified

    # Products
    products_result, count_pages, query_msg, *_ = ProductRepository().find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=is_customer_verified,
    )
    messages += query_msg

    should_fetch_full_data = params.fetch_full_data is True
    should_fetch_attributes = params.fetch_attributes is True or should_fetch_full_data

    customer = None
    if request.user is not None and getattr(request.user, "customer", False):
        customer = request.user.customer

    result = product_collection(
        products_result,
        asdict=True,
        get_sku_list=True,
        is_customer_verified=is_customer_verified,
        include_full_price_data=should_fetch_full_data,
        channel=channel if should_fetch_full_data else None,
        country=country if should_fetch_full_data else None,
        currency=currency if should_fetch_full_data else None,
        customer=customer if should_fetch_full_data else None,
    )

    if len(result) == 3:
        products, sku_list, price_messages = result
        messages += price_messages
    else:
        products, sku_list = result

    if not is_customer_verified:
        messages.append("Your are not verified customer and price query may be limited")

    # Attributes
    if should_fetch_attributes and len(sku_list) > 0:
        messages += fetch_and_attach_attributes(
            products,
            channel=channel,
            language=language,
            use_full_data_features=should_fetch_full_data,
        )

    if params.fetch_variant_groups is True and len(sku_list) > 0:
        variant_groups = ProductVariantGroupRepository(channel, language, country, currency).build_for_skus(sku_list)
        for product in products:
            product["product_variants"] = variant_groups.get(product["sku"], [])

    return PaginatedResponse(
        params.pagination(count=len(products), count_pages=count_pages), products, messages=messages
    )
