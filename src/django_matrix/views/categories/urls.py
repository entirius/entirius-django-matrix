# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import BadRequest, NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.category_url_query import CategoryUrlQuery
from django_matrix.repository.orm.category_urls import CategoryUrlsRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(CategoryUrlQuery.Schema())
@prepare_view
def category_urls_view(request, params: CategoryUrlQuery, *args, **kwargs) -> "Response":
    """
    Returns all URLs for categories based on URL-key or idx.

    Query parameters:
    - idx: List of IDXs to filter by
    - url_key: List of URL keys to filter by
    """
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs, require_channel=False)

    if not params.idx and not params.url_key:
        raise BadRequest("Either 'idx' or 'url_key' parameter is required").add_error(
            "Either 'idx' or 'url_key' parameter is required", "4502"
        )

    repository = CategoryUrlsRepository(channel)
    categories_urls_data = repository.get_categories_urls_data(params)

    if not categories_urls_data:
        raise NotFound("No categories found")

    return Response(categories_urls_data)
