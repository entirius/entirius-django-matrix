# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prices v2 — per-customer pricing. JWT required."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_matrix.api.v2.mixins import ChannelMixin


class PricesView(ChannelMixin, APIView):
    """Per-customer pricing for B2B storefronts."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Per-customer prices",
        description="Batch SKU lookup for customer-specific pricing. JWT required. Cache-Control: private.",
        parameters=[
            OpenApiParameter(name="channel_idx", location="path", description="Channel identifier"),
            OpenApiParameter(name="sku", description="Repeated: ?sku=A&sku=B", many=True),
            OpenApiParameter(name="currency", description="ISO 4217"),
            OpenApiParameter(name="country", description="ISO 3166-1"),
        ],
        responses={
            200: OpenApiResponse(
                description="Per-customer prices keyed by SKU. Same price shape as products/ price object. Empty {} if no data."
            ),
            401: OpenApiResponse(description="JWT required — missing or invalid token"),
        },
        tags=["Matrix Prices"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)
        skus = request.query_params.getlist("sku")

        if not skus:
            return Response({})

        # TODO: Implement per-customer pricing via pricetuner / customer group
        # For now, returns empty — frontend falls back to public price from products/
        data = {}

        response = Response(data)
        response["Cache-Control"] = "private, no-store"
        return response
