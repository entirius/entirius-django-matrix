# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared mixins for v2 views."""

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter
from rest_framework.exceptions import NotFound
from rest_framework.settings import api_settings

from django_matrix.models import Channel
from django_matrix.services.meta import unknown_param_warnings

# Read by get_regional() on every view, so always allowed regardless of what a view declares.
REGIONAL_PARAMS = frozenset({"language", "currency", "country"})

# Consumed by DRF's own content negotiation, never by a view. Reporting it as ignored would be a lie.
FRAMEWORK_PARAMS = frozenset({api_settings.URL_FORMAT_OVERRIDE or "format"})


def known_query_params(parameters: list[OpenApiParameter]) -> frozenset[str]:
    """Static query-param names from an @extend_schema `parameters` list.

    Path params and templated names (`q_{feature_idx}` and friends) are excluded — those are
    matched by prefix, not by name.
    """
    names = {
        param.name
        for param in parameters
        if isinstance(param, OpenApiParameter) and param.location == OpenApiParameter.QUERY and "{" not in param.name
    }
    return frozenset(names) | REGIONAL_PARAMS | FRAMEWORK_PARAMS


class ChannelMixin:
    """Resolves channel + language/currency/country from URL kwargs and query params."""

    # Opt-in: views that surface param.unknown warnings set this from known_query_params().
    known_params: frozenset[str] | None = None

    def get_param_warnings(self) -> list[dict]:
        """`param.unknown` warnings for this request. Empty for views that have not opted in."""
        if self.known_params is None:
            return []
        return unknown_param_warnings(self.request.query_params.keys(), self.known_params)

    def get_channel(self):
        channel_idx = self.kwargs.get("channel_idx")
        try:
            return Channel.objects.get(idx=channel_idx)
        except Channel.DoesNotExist as exc:
            raise NotFound(f"Channel '{channel_idx}' not found") from exc

    def get_regional(self, channel: Channel):
        """Resolve language, currency, country from query params with channel defaults."""
        from django_regional.models import Country, Currency, Language

        lang_iso = self.request.query_params.get("language")
        currency_iso = self.request.query_params.get("currency")
        country_iso = self.request.query_params.get("country")

        language = None
        if lang_iso:
            language = Language.objects.filter(iso2__iexact=lang_iso).first()
        if not language:
            language = channel.default_language

        currency = None
        if currency_iso:
            currency = Currency.objects.filter(iso3__iexact=currency_iso).first()
        if not currency:
            currency = channel.default_currency

        country = None
        if country_iso:
            country = Country.objects.filter(iso2__iexact=country_iso).first()
        if not country:
            country = channel.default_country

        return language, currency, country

    def get_cache_ttl(self, endpoint_key: str) -> int:
        """Get cache TTL from MATRIX_V2_CACHE_TTL settings dict."""
        ttl_dict = getattr(settings, "MATRIX_V2_CACHE_TTL", {})
        return ttl_dict.get(endpoint_key, 300)
