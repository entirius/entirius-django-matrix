# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Options v2 — pre-grouped sort/ranges/filters."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from django_matrix.api.v2.mixins import ChannelMixin
from django_matrix.api.v2.views.product_views import (
    _Q_FILTER_PARAM,
    _R_FILTER_PARAM,
    parse_prefix_params,
    parse_range_params,
)
from django_matrix.schemas.responses.options import OptionsResponse
from django_matrix.services import options_service


class OptionsView(ChannelMixin, APIView):
    @extend_schema(
        summary="Filter and sort options",
        description=(
            "Everything needed to render the filter sidebar, pre-grouped so the frontend renders it "
            "directly — `sort[]`, `ranges[]`, `filters[]`.\n\n"
            "Accepts the same `q_` / `r_` / `category` filters as `products/`. Counts are "
            "**context-sensitive**: pass the currently-active filters and each option's `count` "
            "reflects how many products you would get if you also picked it.\n\n"
            "Example: `?category=sofas&q_color=red`"
        ),
        parameters=[
            OpenApiParameter(name="channel_idx", location="path", description="Channel identifier"),
            OpenApiParameter(name="language", description="ISO 639-1 (defaults to channel language)"),
            OpenApiParameter(name="currency", description="ISO 4217 (defaults to channel currency)"),
            OpenApiParameter(name="country", description="ISO 3166-1 (defaults to channel country)"),
            OpenApiParameter(name="category", description="Narrow options to a category URL key, e.g. `sofas`"),
            _Q_FILTER_PARAM,
            _R_FILTER_PARAM,
        ],
        responses={200: OptionsResponse},
        tags=["Matrix Options"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)

        filters = parse_prefix_params(request.query_params, "q_")
        ranges = parse_range_params(request.query_params, "r_")

        data = options_service.get_options(
            channel=channel,
            language=language,
            currency=currency,
            country=country,
            category=request.query_params.get("category"),
            filters=filters or None,
            ranges=ranges or None,
            show_zeros=True,
        )

        response = Response(data)
        ttl = self.get_cache_ttl("options")
        if ttl > 0:
            response["Cache-Control"] = f"public, max-age=60, s-maxage={ttl}"
        return response
