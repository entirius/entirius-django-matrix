# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared mixins for v2 views."""

from django.conf import settings
from rest_framework.exceptions import NotFound

from django_matrix.models import Channel


class ChannelMixin:
    """Resolves channel + language/currency/country from URL kwargs and query params."""

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
