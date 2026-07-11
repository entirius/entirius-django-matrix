# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.responses import Response

from django_matrix.repository.raw_sql.options import Options as OptionsRepository
from django_matrix.repository.raw_sql.product import Product as ProductRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import OptionsQuery, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(OptionsQuery.Schema())
@prepare_view
def options_listing_view(request, params: OptionsQuery, *args, **kwargs) -> "Response":
    """
    Returns a list of filtering options for products listing,
    with product counts for each filter option
    """

    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    is_customer_verified = False
    if request.user is not None and getattr(request.user, "customer", False):
        if hasattr(request.user.customer, "is_verified"):
            is_customer_verified = request.user.customer.is_verified

    # unlock limit for getting all products
    params.limit = 9999999999

    # Get SQL query for options calculation
    _, _, query_msg, (products_sql, products_sql_params), *_ = ProductRepository().find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=is_customer_verified,
        skip_or_filterable_features=True,
        only_generate_sql=True,
        only_generate_minimal_sql=True,
    )

    options_result = OptionsRepository(
        params=params,
        channel=channel,
        language=language,
        currency=currency,
        country=country,
    ).build_filter_options(
        products_sql=products_sql,
        products_sql_params=products_sql_params,
    )

    messages.extend(query_msg)

    return Response(options_result)
