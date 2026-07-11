# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_utils.api.decorators import api_view, parse_parameters, require_http_method
from django_utils.api.responses import Response

from django_matrix.repository.orm.product_categories import (
    ProductCategories as ProductCategoriesRepository,
)
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import (
    ProductsCategoriesQuery,
    get_view_variable_from_kwargs,
)


@api_view
@require_http_method("GET")
@parse_parameters(ProductsCategoriesQuery.Schema())
@prepare_view
def products_categories_view(request, params: ProductsCategoriesQuery, *args, **kwargs) -> "Response":
    """Returns a paginated response with a list of products"""

    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)

    repository = ProductCategoriesRepository(
        channel=channel, language=language, country=country, currency=currency
    ).throw_api_view_errors(True)

    # Main Query to DB
    categories = repository.find_by_api_query(params=params)

    # as dict
    categories_result = [category.asdict() for category in categories]

    return Response(categories_result, messages=messages)
