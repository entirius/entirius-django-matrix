# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Two read-model fills of one channel do not delete each other's rows.

- the cleanup of a run deletes rows older than the run, never a row a later run stamped
- a fill holds the channel_fill_lock (PostgreSQL session advisory lock) for its whole per-channel body
- a second fill of the same channel waits for the lock; a fill of another channel does not
"""

import threading
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.db import InterfaceError, connection, connections
from django.utils import timezone

from django_matrix.models import Attribute, Channel, ProductRepresentation, ProductT9N
from django_matrix.repository.orm.product import Product as ProductRepository
from django_matrix.tasks import fill_read_model_with_flags
from django_matrix.workers import fill_lock
from django_matrix.workers.fill_lock import channel_fill_lock, channel_lock_key
from django_matrix.workers.fill_read_model_products_and_attributes import fill_read_model_products_and_attributes

postgres_only = pytest.mark.skipif(connection.vendor != "postgresql", reason="advisory locks are PostgreSQL only")

MODELS = [Attribute, ProductT9N, ProductRepresentation]
PARENT_SKU = "RACE-CFG"
THREAD_TIMEOUT = 20


def _matrix_product(channel_full, sku, stamp, product_type="SIMPLE", parent=None):
    """One read-model product with a translation and an attribute, stamped the way a fill run stamps them."""
    ch, lang, _currency, _country = channel_full
    pr = ProductRepresentation.objects.create(
        sku=sku, channel=ch, product_type=product_type, kind_of_product="PHYSICAL", parent=parent, updated_at=stamp
    )
    ProductT9N.objects.create(product_representation=pr, language=lang, name=sku, updated_at=stamp)
    Attribute.objects.create(product=pr, hash=f"hash-{sku}", feature_idx="color", updated_at=stamp)
    return pr


def _stamp(sku, stamp):
    """What a fill of one product does to its rows: every row of the SKU carries the stamp of that run."""
    ProductRepresentation.objects.filter(sku=sku).update(updated_at=stamp)
    ProductT9N.objects.filter(product_representation__sku=sku).update(updated_at=stamp)
    Attribute.objects.filter(product__sku=sku).update(updated_at=stamp)


@pytest.fixture
def pim_configurable(channel_full):
    """An enabled configurable PIM product in the channel, so a fill of the channel writes its row."""
    from django_pim.models import Channel as PimChannel
    from django_pim.models import FeatureSet, Product, RealProduct

    ch, lang, currency, _country = channel_full
    shop = PimChannel.objects.create(idx=ch.idx, name=ch.idx, default_language=lang, default_currency=currency)
    return Product.objects.create(
        product_class=2,
        real_product=RealProduct.objects.create(sku=PARENT_SKU),
        shop=shop,
        feature_set=FeatureSet.objects.create(idx="race"),
        is_enabled=True,
    )


@pytest.fixture
def other_session(db):
    """A second database session: the one a concurrent fill would hold its lock on."""
    session = connections["default"].copy()
    yield session
    session.close()


def _scalar(session, sql, params):
    with session.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()[0]


def _lock_is_free(session, channel):
    key = channel_lock_key(channel)
    if not _scalar(session, "SELECT pg_try_advisory_lock(%s, %s)", key):
        return False
    return _scalar(session, "SELECT pg_advisory_unlock(%s, %s)", key)


def _has_waiter(session, channel):
    """True once another session is queued behind the channel's advisory lock."""
    sql = (
        "SELECT count(*) FROM pg_locks "
        "WHERE locktype = 'advisory' AND classid::bigint = %s AND objid::bigint = %s AND NOT granted "
        "AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
    )
    deadline = time.monotonic() + THREAD_TIMEOUT
    while time.monotonic() < deadline:
        if _scalar(session, sql, channel_lock_key(channel)):
            return True
    return False


def _take_lock_in_thread(channel, logger=None):
    """Start a thread that takes the channel's fill lock on its own connection; the event is set once it holds it."""
    entered = threading.Event()

    def run():
        try:
            with channel_fill_lock(channel, logger):
                entered.set()
        finally:
            connections.close_all()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, entered


# ── The cleanup deletes only rows older than its own run ─────────────


@pytest.mark.parametrize("model", MODELS)
def test_cleanup_keeps_rows_stamped_by_a_later_run(channel_full, model):
    _matrix_product(channel_full, "RACE-LATER", stamp=timezone.now() + timedelta(hours=1))

    fill_read_model_products_and_attributes(channel=channel_full[0], product_class=1)

    assert model.objects.count() == 1


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("stamp_age", [timedelta(hours=1), None])
def test_cleanup_still_deletes_older_and_unstamped_rows(channel_full, model, stamp_age):
    _matrix_product(channel_full, "RACE-GONE", stamp=timezone.now() - stamp_age if stamp_age else None)

    fill_read_model_products_and_attributes(channel=channel_full[0], product_class=1)

    assert model.objects.count() == 0


@pytest.mark.parametrize("model", MODELS)
def test_product_fill_keeps_rows_a_later_run_stamped(channel_full, model):
    _matrix_product(channel_full, "RACE-LATER", stamp=timezone.now() + timedelta(hours=1))

    fill_read_model_products_and_attributes(channel=channel_full[0], product_class=1, product_id="RACE-LATER")

    assert model.objects.count() == 1


def test_full_fill_keeps_a_parent_that_a_product_fill_rewrote_meanwhile(channel_full, pim_configurable):
    """Interleaving 1: the full fill writes the parent, a product fill rewrites it, the full fill cleans up."""
    earlier = timezone.now() - timedelta(hours=1)
    parent = _matrix_product(channel_full, PARENT_SKU, stamp=earlier, product_type="CONFIGURABLE")
    for sku in ("RACE-CFG-S", "RACE-CFG-L"):
        _matrix_product(channel_full, sku, stamp=earlier, parent=parent)
    save_attributes = ProductRepository.attribute_bulk_save

    def product_fill_lands_before_the_cleanup(repository, attributes):
        save_attributes(repository, attributes)
        _stamp(PARENT_SKU, timezone.now() + timedelta(hours=1))

    with patch.object(ProductRepository, "attribute_bulk_save", product_fill_lands_before_the_cleanup):
        fill_read_model_products_and_attributes(channel=channel_full[0], product_class=2)

    # A deleted parent would take its children with it through the foreign key.
    assert set(ProductRepresentation.objects.values_list("sku", flat=True)) == {PARENT_SKU, "RACE-CFG-S", "RACE-CFG-L"}
    assert ProductT9N.objects.filter(product_representation=parent).exists()
    assert Attribute.objects.filter(product=parent).exists()


# ── One fill per channel at a time ───────────────────────────────────


@postgres_only
def test_fill_holds_the_channel_lock_for_its_whole_body(channel_full, other_session):
    """Interleaving 2 cannot happen: no other fill of the channel writes between a fill's writes and its cleanup."""
    ch = channel_full[0]
    free_during_step = []

    def step(**kwargs):
        free_during_step.append(_lock_is_free(other_session, ch))

    # --simple and --attachments are the first and the last step of the per-channel body.
    with (
        patch("django_matrix.tasks.fill_read_model_products_and_attributes", step),
        patch("django_matrix.tasks.fill_read_model_attachments", step),
    ):
        result = fill_read_model_with_flags(channel_idx=ch.idx, simple=True, attachments=True)

    assert result["success"] is True
    assert free_during_step == [False, False]
    assert _lock_is_free(other_session, ch)


@postgres_only
def test_failed_fill_releases_the_channel_lock(channel_full, other_session):
    ch = channel_full[0]

    with patch("django_matrix.tasks.fill_read_model_products_and_attributes", side_effect=RuntimeError("boom")):
        result = fill_read_model_with_flags(channel_idx=ch.idx, simple=True)

    assert result["success"] is False
    assert _lock_is_free(other_session, ch)


@postgres_only
def test_second_fill_of_a_channel_waits_and_then_runs(channel_full, other_session, monkeypatch):
    ch = channel_full[0]
    monkeypatch.setattr(fill_lock, "WAIT_LOG_SECONDS", 0)
    reported = threading.Event()
    logger = MagicMock()
    logger.info.side_effect = lambda message: reported.set()
    key = channel_lock_key(ch)
    _scalar(other_session, "SELECT pg_advisory_lock(%s, %s)", key)

    thread, entered = _take_lock_in_thread(ch, logger)
    try:
        assert _has_waiter(other_session, ch)
        assert reported.wait(THREAD_TIMEOUT)
        assert not entered.is_set()
    finally:
        _scalar(other_session, "SELECT pg_advisory_unlock(%s, %s)", key)
        thread.join(THREAD_TIMEOUT)

    assert entered.is_set()
    assert ch.idx in logger.info.call_args.args[0]
    assert _lock_is_free(other_session, ch)


@postgres_only
def test_fill_of_another_channel_does_not_wait(channel_full, other_session):
    ch = channel_full[0]
    other_channel = Channel.objects.create(idx="race-other", label="Other", default_order="sku")
    key = channel_lock_key(ch)
    _scalar(other_session, "SELECT pg_advisory_lock(%s, %s)", key)

    thread, entered = _take_lock_in_thread(other_channel)
    try:
        assert entered.wait(THREAD_TIMEOUT)
    finally:
        _scalar(other_session, "SELECT pg_advisory_unlock(%s, %s)", key)
        thread.join(THREAD_TIMEOUT)


def test_channel_fill_lock_is_a_noop_outside_postgresql(channel):
    with patch.object(fill_lock, "connection", MagicMock(vendor="sqlite")) as sqlite:
        with channel_fill_lock(channel):
            pass

    sqlite.cursor.assert_not_called()


def test_unlock_that_cannot_run_closes_the_session(channel):
    """A lost connection or an aborted transaction cannot unlock; the lock goes with the session instead."""
    broken = MagicMock(vendor="postgresql")
    cursor = broken.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = [None, InterfaceError("connection already closed")]

    with patch.object(fill_lock, "connection", broken):
        with channel_fill_lock(channel):
            pass

    broken.close.assert_called_once_with()
