# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Omnibus v2 — lowest price in last 30 days (EU Directive 2019/2161)."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_matrix.api.v2.mixins import ChannelMixin
from django_matrix.services import omnibus_service


class OmnibusView(ChannelMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Omnibus prices (30-day lowest)",
        description="EU Directive 2019/2161 compliance. Batch SKU lookup. Public, cached.",
        parameters=[
            OpenApiParameter(name="channel_idx", location="path", description="Channel identifier"),
            OpenApiParameter(name="sku", description="Repeated: ?sku=A&sku=B", many=True),
            OpenApiParameter(name="currency", description="ISO 4217"),
            OpenApiParameter(name="country", description="ISO 3166-1"),
        ],
        responses={
            200: OpenApiResponse(
                description="Omnibus prices keyed by SKU: {SKU: {currency, omnibus_gross, omnibus_net, status}}"
            )
        },
        tags=["Matrix Omnibus"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)
        skus = request.query_params.getlist("sku")

        if not skus:
            return Response({})

        data = omnibus_service.get_omnibus_prices(skus, channel, currency, country)

        response = Response(data)
        ttl = self.get_cache_ttl("omnibus")
        if ttl > 0:
            response["Cache-Control"] = f"public, max-age=60, s-maxage={ttl}"
        return response
