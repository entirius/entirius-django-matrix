# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import tee

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.responses import Response

from django_matrix.repository.orm.variants import Variants as VariantsRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import VariantsQuery, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(VariantsQuery.Schema())
@prepare_view
def products_variants_view(request, params: VariantsQuery, url_key: str, *args, **kwargs) -> "Response":
    """Returns a paginated response with a list of products"""
    params.url_key = url_key

    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)

    repository = VariantsRepository(
        channel=channel, language=language, country=country, currency=currency
    ).throw_api_view_errors(True)

    # Main Query to DB
    products_in_matrix, feature_set_idx, query_msg = repository.find_by_api_query(params=params)
    messages += query_msg

    products_in_matrix_products, products_in_matrix_options = tee(products_in_matrix)

    # Organize data
    options, query_msg = repository.resolve_options(products_in_matrix_options, feature_set_idx)
    messages += query_msg

    products, messages = repository.resolve_products(products_in_matrix_products)
    messages += query_msg

    # As dict
    options_result = [option.asdict() for option in options]
    products_result = [product.asdict() for product in products]

    return Response({"options": options_result, "products": products_result}, messages=messages)
