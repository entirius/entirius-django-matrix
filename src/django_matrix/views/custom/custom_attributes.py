# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from itertools import chain, groupby

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import BadRequest, NotFound
from django_utils.api.responses import Response
from django_utils.api.utils import make_media_url

from django_matrix.dto.view.attribute import AttributeDetailDTO, CustomFeature
from django_matrix.enums import ProductType
from django_matrix.models import ProductRepresentation
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import AttributeCustomListingQuery, get_view_variable_from_kwargs

logger = logging.getLogger(__name__)


def f9e_to_a9e_factory(attrs, language):
    try:
        from django_pim.models import FeatureType, FrontendInputType
    except:
        raise BadRequest("Unknown error")

    data = (
        attrs.distinct()
        .values(
            "feature__idx",
            "feature__feature_type",
            f"feature__name_t9n__{language.iso2}",
            "idx",
            "display_order",
            f"name_t9n__{language.iso2}",
            "feature__feature_in_feature_set__position",
            "feature__is_required",
            "feature__frontend_input_type",
            "feature__excluded_color_hash",
            "is_default",
            "picture",
            "color_hash",
            f"group__name_t9n__{language.iso2}",
        )
        .order_by("display_order")
    )
    response_data = []
    feature_as_key = lambda x: (
        x["feature__idx"],
        x[f"feature__name_t9n__{language.iso2}"],
        x["feature__feature_type"],
        x["feature__feature_in_feature_set__position"],
        x["feature__is_required"],
        x["feature__frontend_input_type"],
        x["feature__excluded_color_hash"],
    )
    for feature_details, feature_group in groupby(sorted(data, key=feature_as_key), key=feature_as_key):
        (
            feature_idx,
            feature_name,
            feature_type,
            position,
            feature_is_required,
            frontend_input_type,
            excluded_color_hash,
        ) = feature_details
        feature_attributes = []
        for attr in feature_group:
            feature_attributes.append(
                AttributeDetailDTO(
                    idx=attr["idx"],
                    name=attr[f"name_t9n__{language.iso2}"],
                    is_default=attr["is_default"],
                    picture=make_media_url(attr["picture"]),
                    color_hash=attr["color_hash"],
                    group=(
                        attr[f"group__name_t9n__{language.iso2}"]
                        if f"group__name_t9n__{language.iso2}" in attr
                        else None
                    ),
                ).asdict()
            )

        response_data.append(
            CustomFeature(
                idx=feature_idx,
                name=feature_name,
                attributes=feature_attributes,
                position=position,
                feature_type=FeatureType.labels.get(feature_type),
                frontend_input_type=FrontendInputType.labels.get(frontend_input_type),
                is_required=feature_is_required,
                excluded_color_hash=excluded_color_hash,
            ).asdict()
        )
    return response_data


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(AttributeCustomListingQuery.Schema())
@prepare_view
def get_custom_attributes(request, params: AttributeCustomListingQuery, *args, **kwargs) -> "Response":
    """Returns product custom attributes"""
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    if not params.basic_sku:
        raise NotFound("Basic sku is required")

    try:
        from django_pim.models import ProductAttribute
    except:
        raise BadRequest("Unknown error")

    product_custom = (
        ProductRepresentation.objects.filter(
            sku=params.basic_sku, product_type=ProductType.PRODUCT_CUSTOM, channel=channel
        )
        .first()
        .sku
    )
    if not product_custom:
        raise BadRequest("Product custom not found")
    if params.only_chosen:
        # get choosen/default attributes for custom
        attributes, all_attr_modifier, errors = ProductAttribute.objects.get_custom_attributes_idx(
            product_custom,
            list(chain.from_iterable([a9e for f9e, a9e in params.chosen_f9e_to_a9e.items()])),
            channel.idx,
        )
    else:
        # get all available attributes for custom
        attributes, errors = ProductAttribute.objects.get_all_available_attributes(
            product_custom,
            list(chain.from_iterable([a9e for f9e, a9e in params.chosen_f9e_to_a9e.items()])),
            channel.idx,
        )
    response_dict = f9e_to_a9e_factory(attributes, language)

    return Response(response_dict, messages=messages, errors=errors)
