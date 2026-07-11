# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stable codes for non-blocking filter/sort feedback surfaced in v2 `meta.warnings`.

Each user-supplied `q_`/`r_`/`s_` param that the backend cannot apply produces a
warning `{code, param, message}` instead of being silently dropped. Codes are stable
machine-readable identifiers (RFC 7807-like); messages reuse the repository diagnostics.
"""


class WarningCode:
    # Sort (s_<field>)
    SORT_NOT_SORTABLE = "sort.not_sortable"
    SORT_UNKNOWN_FIELD = "sort.unknown_field"
    SORT_INVALID = "sort.invalid"

    # Filter (q_<feature>) / range (r_<feature>)
    FILTER_NOT_FILTERABLE = "filter.not_filterable"
    FILTER_UNSUPPORTED_TYPE = "filter.unsupported_type"
    FILTER_INVALID = "filter.invalid"
