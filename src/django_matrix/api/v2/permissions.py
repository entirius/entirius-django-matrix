# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Permissions for v2 API endpoints."""

from rest_framework.permissions import AllowAny, IsAuthenticated


class IsOptionalAuth(AllowAny):
    """Public endpoint — auth optional. Used for most storefront endpoints."""

    pass


class IsJWTRequired(IsAuthenticated):
    """JWT required — used for prices/ (per-customer pricing)."""

    pass
