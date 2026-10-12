# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Categories v2 — nested tree, lazy subtree, or batch single with SEO."""

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_matrix.api.v2.mixins import ChannelMixin
from django_matrix.services import category_service

DEFAULT_MAX_URL_KEYS = 50


class CategoriesView(ChannelMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Category tree, lazy subtree, or batch single",
        description=(
            "Default: nested tree (is_in_menu=true); every node carries has_children. "
            "?url_key=: single or batch category lookup with SEO fields (repeatable, ignores "
            "is_in_menu) → {results: [...]}. "
            "?parent_url_key=: subtree rooted at the parent's children (repeatable, merged). "
            "?depth=N limits levels counted from the response top (depth=1 → one level / lazy); "
            "omit for full depth. All categories include url_keys dict {lang: url_key} for hreflang SEO."
        ),
        parameters=[
            OpenApiParameter(name="channel_idx", location="path", description="Channel identifier"),
            OpenApiParameter(name="language", description="ISO 639-1"),
            OpenApiParameter(
                name="url_key",
                description="Single or batch lookup. Repeatable: ?url_key=a&url_key=b → {results: [...]}",
                many=True,
            ),
            OpenApiParameter(name="depth", description="Max tree depth (1 = one level / lazy; omit = full)", type=int),
            OpenApiParameter(
                name="parent_url_key",
                description="Subtree root(s). Repeatable: ?parent_url_key=a&parent_url_key=b",
                many=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Category tree (list, nodes have has_children) or single/batch wrapped in {results: []}"
            )
        },
        tags=["Matrix Categories"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)

        url_keys = request.query_params.getlist("url_key")
        if url_keys:
            max_keys = getattr(settings, "MATRIX_V2_CATEGORIES_MAX_URL_KEYS", DEFAULT_MAX_URL_KEYS)
            if len(url_keys) > max_keys:
                raise ValidationError(f"Too many url_key values (max {max_keys}).")
            results = category_service.get_categories(channel, language, url_keys)
            response = Response({"results": results})
        else:
            depth = request.query_params.get("depth")
            tree = category_service.get_category_tree(
                channel,
                language,
                depth=int(depth) if depth else None,
                parent_url_keys=request.query_params.getlist("parent_url_key") or None,
            )
            response = Response(tree)

        ttl = self.get_cache_ttl("categories")
        if ttl > 0:
            response["Cache-Control"] = f"public, max-age=60, s-maxage={ttl}"
        return response
