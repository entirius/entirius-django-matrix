# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_utils.api.decorators import api_view, parse_parameters, require_http_method
from django_utils.api.responses import Response

from django_matrix.dto.view.attribute import attribute_collection
from django_matrix.repository.raw_sql.attribute import Attribute as AttributeRepository
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import AttributeQuery, get_view_variable_from_kwargs


@api_view
@require_http_method("GET")
@parse_parameters(AttributeQuery.Schema())
@prepare_view
def attributes_extended_listing_view(request, params: AttributeQuery, feature_type: str, *args, **kwargs) -> "Response":
    """Returns a paginated response with a list of attributes with specified type"""

    # These variables are prepared by prepare_view decorator. Don't mess with this
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)

    # Attributes
    attributes_result, attr_msg = AttributeRepository().find_by_api_query(
        params=params, channel=channel, language=language, feature_type=feature_type.upper(), is_full_view=True
    )
    messages += attr_msg

    attributes = attribute_collection(attributes_result, asdict=True, language_iso2=language.iso2)

    return Response(attributes, messages=messages)
