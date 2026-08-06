# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Response `meta` envelope for non-blocking q_/r_/s_ feedback.

`warnings` is the list of `{code, param, message}` produced by the repository for any
filter/sort param it could not apply, plus the view-level `param.unknown` entries for
params the endpoint does not read at all. Empty warnings → status "ok" ("everything applied").
"""

from collections.abc import Collection, Iterable

from django_matrix.repository.raw_sql.warning_codes import WarningCode

STATUS_OK = "ok"
STATUS_WARNING = "warning"

# Feature-scoped params. The suffix is a PIM feature idx resolved per channel, so the set
# cannot be enumerated statically — the repository warns when it cannot apply one.
DYNAMIC_PARAM_PREFIXES = ("q_", "r_", "s_")

# The endpoints are public and uncapped input is reflected back, so bound what a caller can inflate.
MAX_UNKNOWN_PARAM_WARNINGS = 10
MAX_PARAM_NAME_LENGTH = 64


def build_meta(warnings: list[dict] | None) -> dict:
    warnings = warnings or []
    return {"status": STATUS_WARNING if warnings else STATUS_OK, "warnings": warnings}


def unknown_param_warnings(param_names: Iterable[str], known: Collection[str]) -> list[dict]:
    """Warn, never reject, for query params the endpoint does not read.

    Rejecting would break consumers that forward the whole browser query string
    (tracking params on a category URL would fail the page).
    """
    unknown = [name for name in param_names if name not in known and not name.startswith(DYNAMIC_PARAM_PREFIXES)]
    warnings = [_unknown_param_warning(name) for name in unknown[:MAX_UNKNOWN_PARAM_WARNINGS]]
    if len(unknown) > MAX_UNKNOWN_PARAM_WARNINGS:
        dropped = len(unknown) - MAX_UNKNOWN_PARAM_WARNINGS
        warnings.append(
            {
                "code": WarningCode.PARAM_UNKNOWN_TRUNCATED,
                "param": None,
                "message": f"{dropped} further unknown query params were ignored",
            }
        )
    return warnings


def _unknown_param_warning(name: str) -> dict:
    """The param name is caller-controlled and gets echoed back, so cap it."""
    shown = name[:MAX_PARAM_NAME_LENGTH]
    return {
        "code": WarningCode.PARAM_UNKNOWN,
        "param": shown,
        "message": f"unknown query param '{shown}' was ignored",
    }
