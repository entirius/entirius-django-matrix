# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Connections of the parallel listing queries.

`execute_parallel_queries` runs the product list and its COUNT in two pool threads. Django keeps a
connection per thread and closes it when a request ends, which never happens in a pool thread: every
listing left two idle connections until garbage collection, and under load Postgres refused new
clients ("too many clients already", a 500 on every API call). Each pool thread now closes its own.
"""

import pytest
from django.db import connection

from django_matrix.repository.raw_sql import DbConnect


def _backends() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        return cursor.fetchone()[0]


@pytest.mark.django_db(transaction=True)
def test_parallel_queries_answer_and_leave_no_connection_open():
    db = DbConnect()
    before = _backends()

    for _ in range(5):
        rows, count = db.execute_parallel_queries("SELECT 1 AS one", {}, "SELECT 7", {})
        assert rows == [{"one": 1}]
        assert count == 7

    assert _backends() == before
