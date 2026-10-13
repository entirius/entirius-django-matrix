# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""One read-model fill per channel at a time.

A fill stamps the rows it writes and ends by deleting the older ones, so two fills that overlap on a channel
would delete each other's rows. The lock is a PostgreSQL session advisory lock: it holds for every caller
(Celery tasks and the management command) and vanishes with the connection when the process dies.
"""

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from django.db import Error, connection
from process_logger import ProcessLogger

from django_matrix.models import Channel

# First key of the two-key advisory lock ("MXFL" in ASCII); the second key is the channel id.
FILL_LOCK_NAMESPACE = 0x4D58464C
WAIT_LOG_SECONDS = 5

module_logger = logging.getLogger(__name__)


def channel_lock_key(channel: Channel) -> tuple[int, int]:
    return FILL_LOCK_NAMESPACE, channel.pk


def _report_wait(channel: Channel, logger: ProcessLogger | None) -> None:
    (logger or module_logger).info(
        f"Fill of channel {channel.idx} has waited {WAIT_LOG_SECONDS} s for another fill of this channel"
    )


def _acquire(channel: Channel, logger: ProcessLogger | None) -> None:
    timer = threading.Timer(WAIT_LOG_SECONDS, _report_wait, [channel, logger])
    timer.start()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s, %s)", channel_lock_key(channel))
    finally:
        timer.cancel()


def _release(channel: Channel) -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s, %s)", channel_lock_key(channel))
            held = cursor.fetchone()[0]
    except Error:
        # A broken connection or an aborted transaction cannot run the unlock: ending the session releases the lock.
        connection.close()
        return
    if not held:
        module_logger.warning(f"Fill of channel {channel.idx} ended without the fill lock of this channel")


@contextmanager
def channel_fill_lock(channel: Channel, logger: ProcessLogger | None = None) -> Iterator[None]:
    """Hold the fill lock of one channel; waits for a running fill of that channel. A no-op outside PostgreSQL."""
    if connection.vendor != "postgresql":
        yield
        return
    try:
        _acquire(channel, logger)
        yield
    finally:
        _release(channel)
