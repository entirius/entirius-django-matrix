# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test URL conf — mounts the real production urlconf (v2 + v1).

The v1 chain is importable since ``dto/view/price.py`` defers its
``django_accounts`` import; keep the full urlconf mounted so URL-pattern
regressions (e.g. ``stock/<path:sku>/``) are caught by tests.
"""

from django_matrix.urls import urlpatterns  # noqa: F401
