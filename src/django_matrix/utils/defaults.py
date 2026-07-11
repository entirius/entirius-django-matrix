# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.core.exceptions import ObjectDoesNotExist
from django_regional.models import Country, Currency, Language
from django_utils.api.exceptions import BadRequest

from django_matrix.models.channel import Channel


def get_language(channel: Channel, requested: str | None) -> (Language, str | None):
    requested = requested.lower() if isinstance(requested, str) else requested
    try:
        language = channel.languages.get(iso2=requested)
    except ObjectDoesNotExist:
        language = None
    if not language:
        default = channel.default_language
        if default:
            msg = "Requested language is not supported." if requested is not None else "Empty language request."
            return default, f"{msg} Using channel default: {default.iso2}."
        else:
            raise BadRequest(f"Channel {channel.idx} doesn't have a default language and requested is not supported.")
    else:
        return language, None


def get_currency(channel: Channel, requested: str | None) -> (Currency, str | None):
    requested = requested.upper() if isinstance(requested, str) else requested
    try:
        currency = channel.currencies.get(iso3=requested)
    except ObjectDoesNotExist:
        currency = None
    if not currency:
        default = channel.default_currency
        if default:
            msg = "Requested currency is not supported." if requested is not None else "Empty currency request."
            return default, f"{msg} Using channel default: {default.iso3}."
        else:
            raise BadRequest(f"Channel {channel.idx} doesn't have a default currency and requested is not supported.")
    else:
        return currency, None


def get_country(channel: Channel, requested: str | None) -> (Country, str | None):
    requested = requested.upper() if isinstance(requested, str) else requested
    try:
        country = channel.countries.get(iso2=requested)
    except ObjectDoesNotExist:
        country = None
    if not country:
        default = channel.default_country
        if default:
            msg = "Requested country is not supported." if requested is not None else "Empty country request."
            return default, f"{msg} Using channel default: {default.iso2}."
        else:
            raise BadRequest(f"Channel {channel.idx} doesn't have a default country and requested is not supported.")
    else:
        return country, None
