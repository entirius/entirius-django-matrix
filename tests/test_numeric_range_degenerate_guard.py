# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A mass/temperature/length slider must not reach /options/ when min == max.

A range collapsed to a single point filters nothing and renders as a dead control on the
storefront — that is what a category holding exactly one product with the feature produces.
DECIMAL ranges already drop these in SQL via ``HAVING MIN != MAX``; this path does not go
through that query, so it drops them itself.

DB-free: the repository is built without ``__init__`` and only the range loop is exercised.
"""

from types import SimpleNamespace

import pytest

from django_matrix.repository.raw_sql import options as options_module


@pytest.fixture
def repo(monkeypatch):
    """Options instance carrying only what ``_add_numeric_feature_ranges`` reads."""
    repo = object.__new__(options_module.Options)
    repo.base_sql_params = {}
    repo.result_data = []
    repo.language = SimpleNamespace(iso2="en")
    repo.fetch_all = lambda sql, params: [{"feature_idx": "weight", "feature_name": "Weight", "position": 10}]

    monkeypatch.setattr(
        options_module,
        "Feature",
        SimpleNamespace(
            objects=SimpleNamespace(get=lambda **kw: SimpleNamespace(get_cls_unit_conversion=lambda: ("g", object)))
        ),
    )
    monkeypatch.setattr(options_module, "convert_bounds_for_lang", lambda cls, low, high, iso2: (low, high, "g"))
    return repo


def test_degenerate_range_is_dropped(repo):
    repo._fetch_numeric_feature_min_max = lambda idx, sql, params: (500, 500)

    repo._add_numeric_feature_ranges(None, None)

    assert repo.result_data == []


def test_real_range_still_returned(repo):
    repo._fetch_numeric_feature_min_max = lambda idx, sql, params: (180, 500)

    repo._add_numeric_feature_ranges(None, None)

    assert len(repo.result_data) == 1
    assert (repo.result_data[0].min_value, repo.result_data[0].max_value) == (180, 500)
