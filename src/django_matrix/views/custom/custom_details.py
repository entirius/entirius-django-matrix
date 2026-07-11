# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.attribute import attribute_collection
from django_matrix.repository.raw_sql.custom_details import CustomDetails
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import AttributeCustomQuery, get_view_variable_from_kwargs

logger_process = logging.getLogger("process")


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(AttributeCustomQuery.Schema())
@prepare_view
def get_custom_details(request, params: AttributeCustomQuery, *args, **kwargs) -> "Response":
    """Returns product custom attributes"""
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    if not params.basic_sku:
        raise NotFound("Basic sku is required")

    custom_details = CustomDetails(
        params=params, channel=channel, language=language, country=country, currency=currency
    )
    try:
        attributes_result, attr_result_list, price, attr_msg, errors = custom_details.get_attributes_details()
    except Exception as e:
        logger_process.exception(e)
        raise NotFound("Product custom details not found")
    messages += attr_msg
    pictures_result, pic_msg = custom_details.get_pictures(attr_result_list)
    messages += pic_msg
    attributes = attribute_collection(attributes_result, asdict=True, language_iso2=language.iso2)
    response_dict = {"custom_specification": attributes, "price": price, "pictures": pictures_result}

    return Response(response_dict, messages=messages, errors=errors)
