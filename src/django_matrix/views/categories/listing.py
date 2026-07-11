# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.responses import Response

from django_matrix.repository.orm.categories import CategoriesRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import CategoryListingQuery, get_view_variable_from_kwargs


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(CategoryListingQuery.Schema())
@prepare_view
def categories_listing_view(request, params: CategoryListingQuery, *args, **kwargs) -> "Response":
    """
    Returns a list of categories for the channel, without pagination.

    Query parameters:
    - language: ISO 639-1 language code
    - depth: Filter by tree depth (e.g. depth=1 for top-level only)
    - url_key: Filter by URL key(s)
    - parent_url_key: Filter by parent category URL key
    """
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    repository = CategoriesRepository(channel)
    categories = repository.get_categories(params, language.iso2)
    return Response(categories, messages=messages)
