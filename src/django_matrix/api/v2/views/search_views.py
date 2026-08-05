# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Search v2 — unified search with scope param."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from django_matrix.api.v2.mixins import ChannelMixin, known_query_params
from django_matrix.api.v2.views.product_views import (
    _CHANNEL_PARAM,
    _Q_FILTER_PARAM,
    _R_FILTER_PARAM,
    _REGIONAL_PARAMS,
    _S_SORT_PARAM,
    _safe_int,
    parse_page,
    parse_prefix_params,
    parse_range_params,
    parse_sort_params,
)
from django_matrix.services import search_service

# Declared once, consumed twice: by @extend_schema and by known_query_params (param.unknown).
SEARCH_PARAMS = [
    _CHANNEL_PARAM,
    *_REGIONAL_PARAMS,
    OpenApiParameter(name="q", description="Search query (min 2 chars)", required=True),
    OpenApiParameter(name="scope", description="Comma-separated sections to return (default: `products,categories`)"),
    OpenApiParameter(
        name="limit",
        description="Max results per section (default: 5 for suggest, page_size for listing)",
        type=int,
    ),
    OpenApiParameter(name="page", description="Page number (1-based)", type=int),
    OpenApiParameter(name="page_size", description="Results per page (default 12, max 100)", type=int),
    OpenApiParameter(name="category", description="Narrow search to a category URL key, e.g. `sofas`"),
    _Q_FILTER_PARAM,
    _R_FILTER_PARAM,
    _S_SORT_PARAM,
]


class SearchView(ChannelMixin, APIView):
    known_params = known_query_params(SEARCH_PARAMS)

    @extend_schema(
        summary="Unified search",
        description=(
            "Unified full-text + fuzzy search across products and categories. Returns "
            "`{products: {total, results, has_next_page}, categories: {results}, phrases: []}`.\n\n"
            "The product section accepts the same `q_` / `r_` filters as `products/` to narrow results.\n\n"
            "Example: `?q=sofa&scope=products,categories`"
        ),
        parameters=SEARCH_PARAMS,
        responses={
            200: OpenApiResponse(
                description=(
                    "Search results: {products: {total, results, has_next_page}, categories: {results}, "
                    "phrases: [], meta: {status, warnings: [{code, param, message}]}}"
                )
            )
        },
        tags=["Matrix Search"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)

        scope = request.query_params.get("scope", "products,categories")
        limit = _safe_int(request.query_params.get("limit"), 5)
        page = parse_page(request.query_params.get("page"))
        page_size = min(_safe_int(request.query_params.get("page_size"), 12), 100)

        filters = parse_prefix_params(request.query_params, "q_")
        ranges = parse_range_params(request.query_params, "r_")

        data = search_service.search(
            channel=channel,
            language=language,
            currency=currency,
            country=country,
            query=request.query_params.get("q", ""),
            scope=scope,
            limit=limit,
            category=request.query_params.get("category"),
            filters=filters or None,
            ranges=ranges or None,
            sort=parse_sort_params(request.query_params, "s_") or None,
            page=page,
            page_size=page_size,
            extra_warnings=self.get_param_warnings(),
        )

        response = Response(data)
        ttl = self.get_cache_ttl("search")
        if ttl > 0:
            response["Cache-Control"] = f"public, max-age=60, s-maxage={ttl}"
        return response
