# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stock v2 — real-time batch SKU lookup. Never cached."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from django_matrix.api.v2.mixins import ChannelMixin
from django_matrix.services import stock_service


class StockView(ChannelMixin, APIView):
    @extend_schema(
        summary="Real-time stock",
        description=(
            "Batch SKU stock lookup. Never cached (Cache-Control: no-store). "
            "Use for cart validation — not the on_stock bool from products/ (which may be stale). "
            "Returns dict keyed by SKU. Missing SKU = absent from response. No QMS module = empty {}."
        ),
        parameters=[
            OpenApiParameter(name="channel_idx", location="path", description="Channel identifier"),
            OpenApiParameter(name="sku", description="Repeated: ?sku=A&sku=B", many=True, required=True),
        ],
        responses={
            200: OpenApiResponse(
                description="Stock data keyed by SKU",
                response=inline_serializer(
                    name="StockResponse",
                    fields={
                        "SKU-001": inline_serializer(
                            name="StockItem",
                            fields={
                                "quantity": serializers.IntegerField(help_text="Available quantity"),
                                "is_in_stock": serializers.BooleanField(help_text="True if quantity > 0"),
                            },
                        )
                    },
                ),
            )
        },
        tags=["Matrix Stock"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        skus = request.query_params.getlist("sku")

        if not skus:
            return Response({})

        data = stock_service.get_stock_for_skus(skus, channel.idx)

        response = Response(data)
        response["Cache-Control"] = "no-store"
        return response
