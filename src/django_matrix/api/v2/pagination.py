# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pagination constants for v2 storefront API.

Pagination is handled in the service layer (LIMIT+1 trick for has_next_page).
Views use these constants for defaults.
"""

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 100
