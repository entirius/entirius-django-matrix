# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import wraps

from django.core.exceptions import ObjectDoesNotExist
from django_utils.api.exceptions import NotFound

from django_matrix.models.channel import Channel
from django_matrix.utils.defaults import get_country, get_currency, get_language


def prepare_view(view):
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        channel = None
        (params,) = args
        if "channel_idx" not in kwargs:
            language = params.language
            currency = params.currency
            country = params.country

        else:
            channel_idx = kwargs["channel_idx"]
            try:
                channel = Channel.objects.get(idx=channel_idx)
            except ObjectDoesNotExist:
                raise NotFound(f"Channel {channel_idx} does not exist")
            kwargs["channel"] = channel

            messages = []
            language, msg = get_language(channel, params.language)
            if msg is not None:
                messages.append(msg)
            kwargs["language"] = language

            currency, msg = get_currency(channel, params.currency)
            if msg is not None:
                messages.append(msg)
            kwargs["currency"] = currency

            country, msg = get_country(channel, params.country)
            if msg is not None:
                messages.append(msg)
            kwargs["country"] = country

            kwargs["messages"] = messages

        return view(request, *args, **kwargs).add_regional(
            language=getattr(language, "iso2", None),
            currency=getattr(currency, "iso3", None),
            country=getattr(country, "iso2", None),
        )

    return _wrapped
