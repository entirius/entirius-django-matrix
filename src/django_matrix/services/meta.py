# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Response `meta` envelope for non-blocking q_/r_/s_ feedback.

`warnings` is the list of `{code, param, message}` produced by the repository for any
filter/sort param it could not apply. Empty warnings → status "ok" ("everything applied").
"""

STATUS_OK = "ok"
STATUS_WARNING = "warning"


def build_meta(warnings: list[dict] | None) -> dict:
    warnings = warnings or []
    return {"status": STATUS_WARNING if warnings else STATUS_OK, "warnings": warnings}
