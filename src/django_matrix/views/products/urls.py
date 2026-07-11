# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import BadRequest, NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.product_url_query import ProductUrlQuery
from django_matrix.repository.orm.product_urls import ProductUrlsRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(ProductUrlQuery.Schema())
@prepare_view
def product_urls_view(request, params: ProductUrlQuery, *args, **kwargs) -> "Response":
    """
    Returns all URLs for products based on URL-key or SKU.

    Query parameters:
    - sku: List of SKUs to filter by
    - url_key: List of URL keys to filter by
    """
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs, require_channel=False)

    if not params.sku and not params.url_key:
        raise BadRequest("Either 'sku' or 'url_key' parameter is required").add_error(
            "Either 'sku' or 'url_key' parameter is required", "4501"
        )

    repository = ProductUrlsRepository(channel)
    products_urls_data = repository.get_products_urls_data(params)

    if not products_urls_data:
        raise NotFound("No products found")

    return Response(products_urls_data)
