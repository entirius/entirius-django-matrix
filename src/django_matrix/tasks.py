# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Celery tasks for django_matrix.

This module provides shared tasks that can be called both:
1. Directly from management commands (synchronous execution)
2. Via Celery queue (asynchronous execution)
"""

import sys
import time
from contextlib import contextmanager
from io import StringIO

from celery import shared_task
from django.core.cache import caches
from process_logger import ProcessLogger

from django_matrix.models import Channel

PENDING_KEY = "pim:matrix:pending"
LOCK_KEY = "pim:matrix:flush_scheduled"
LAST_FLUSH_KEY = "pim:matrix:last_flush"
CHANNEL_REBUILD_SENTINEL = "__CHANNEL_REBUILD__"


@contextmanager
def suppress_stdout():
    """Suppress stdout during execution to avoid verbose logging in Celery"""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout


from django_matrix.workers.fill_read_model_attachments import fill_read_model_attachments
from django_matrix.workers.fill_read_model_pictures_and_thumbs import fill_read_model_pictures_and_thumbs
from django_matrix.workers.fill_read_model_products_and_attributes import fill_read_model_products_and_attributes
from django_matrix.workers.fill_read_model_videos import fill_read_model_videos


def fill_read_model_with_flags(
    channel_idx: str | None = None,
    product_id: str | None = None,
    custom: bool = False,
    bundle: bool = False,
    config: bool = False,
    simple: bool = False,
    prices: bool = False,
    onstock: bool = False,
    pictures: bool = False,
    videos: bool = False,
    attachments: bool = False,
    logger: ProcessLogger | None = None,
):
    """
    Fill read model with granular control over which steps to execute.

    This function provides the shared logic for both the management command
    and Celery tasks, allowing fine-grained control over which processing
    steps to execute.

    Args:
        channel_idx: Specific channel to update (default: all channels)
        product_id: Product SKU to update (default: all products)
        custom: Process custom products (product_class=4)
        bundle: Process bundle products (product_class=3)
        config: Process config products (product_class=2)
        simple: Process simple products (product_class=1)
        prices: Process prices
        onstock: Process on stock status
        pictures: Process pictures and thumbs
        videos: Process videos
        logger: ProcessLogger instance (optional)

    Returns:
        dict: Result with success status and details
    """
    if logger:
        logger.info("Starting fill read model with flags")
        if channel_idx:
            logger.add_log_param("channel_idx", channel_idx)
        if product_id:
            logger.add_log_param("product_id", product_id)

    # Get channels
    if channel_idx:
        channels = Channel.objects.filter(idx=channel_idx)
    else:
        channels = Channel.objects.all()

    if not channels.exists():
        error_msg = "No channels found in Matrix"
        if logger:
            logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # Check if all flags are False (meaning run all steps)
    all_flags_false = all(
        [
            not custom,
            not bundle,
            not config,
            not simple,
            not prices,
            not onstock,
            not pictures,
            not videos,
            not attachments,
        ]
    )

    results = []

    for channel in channels:
        channel_result = {"channel_idx": channel.idx, "steps": []}

        if logger:
            logger.info(f"Processing channel {channel.idx}")

        try:
            with suppress_stdout():
                if custom or all_flags_false:
                    if logger:
                        logger.info("Filling custom products")
                    fill_read_model_products_and_attributes(channel=channel, product_class=4, product_id=product_id)
                    channel_result["steps"].append("customs")

                if bundle or all_flags_false:
                    if logger:
                        logger.info("Filling bundle products")
                    fill_read_model_products_and_attributes(channel=channel, product_class=3, product_id=product_id)
                    channel_result["steps"].append("bundle")

                if config or all_flags_false:
                    if logger:
                        logger.info("Filling config products")
                    fill_read_model_products_and_attributes(channel=channel, product_class=2, product_id=product_id)
                    channel_result["steps"].append("config")

                if simple or all_flags_false:
                    if logger:
                        logger.info("Filling simple products")
                    fill_read_model_products_and_attributes(channel=channel, product_class=1, product_id=product_id)
                    channel_result["steps"].append("simple")

                if prices or all_flags_false:
                    from django_matrix.workers.fill_read_model_prices import fill_read_model_prices

                    if logger:
                        logger.info("Filling prices")
                    fill_read_model_prices(channel=channel, product_id=product_id)
                    channel_result["steps"].append("prices")

                if onstock or all_flags_false:
                    from django_matrix.workers.fill_read_model_on_stock import fill_read_model_on_stock_batch

                    if logger:
                        logger.info("Filling on stock status")
                    fill_read_model_on_stock_batch(channel=channel, product_id=product_id)
                    channel_result["steps"].append("onstock")

                if pictures or all_flags_false:
                    if logger:
                        logger.info("Filling pictures and thumbs")
                    fill_read_model_pictures_and_thumbs(channel=channel, product_id=product_id)
                    channel_result["steps"].append("pictures")

                if videos or all_flags_false:
                    if logger:
                        logger.info("Filling videos")
                    fill_read_model_videos(channel=channel, product_id=product_id)
                    channel_result["steps"].append("videos")

                if attachments or all_flags_false:
                    if logger:
                        logger.info("Filling attachments")
                    fill_read_model_attachments(channel=channel, product_id=product_id)
                    channel_result["steps"].append("attachments")

            channel_result["success"] = True

        except Exception as e:
            error_msg = f"Failed to fill read model for channel {channel.idx}: {str(e)}"
            if logger:
                logger.exception(e)
            channel_result["success"] = False
            channel_result["error"] = str(e)

        results.append(channel_result)

    success = all(r.get("success", False) for r in results)

    if logger:
        if success:
            logger.info(f"Successfully processed {len(results)} channels")
        else:
            logger.error("Failed to process some channels")

    return {"success": success, "channels_processed": len(results), "results": results}


@shared_task(queue="matrix_pull")
def fill_read_model_for_product_task(product_id: str, channel_idx: str | None = None, runned_at: str | None = None):
    """
    Celery task wrapper for fill_read_model_for_product.

    This task is triggered after journal log processing to ensure
    the Matrix read model is synchronized with the latest PIM data.

    Args:
        product_id: Product SKU to update
        channel_idx: Specific channel to update (default: all channels)
        runned_at: ISO timestamp when task was initiated (for tracking)

    Queue: fill_read_model_silent (separate queue to avoid verbose logging)
           Run a dedicated worker for this queue: celery -A main worker -Q fill_read_model_silent -l error

    Returns:
        dict: Result with success status and details
    """
    logger = ProcessLogger("matrix.fill_read_model")
    logger.set_code(5200)
    logger.add_log_param("product_id", product_id)

    try:
        logger.info(f"Starting fill read model for product {product_id}")
        if channel_idx:
            logger.add_log_param("channel_idx", channel_idx)

        result = fill_read_model_with_flags(channel_idx=channel_idx, product_id=product_id, logger=logger)

        if logger:
            if result["success"]:
                logger.info(
                    f"Successfully filled read model for product {product_id} across {result['channels_processed']} channels"
                )
            else:
                logger.error(f"Failed to fill read model for product {product_id}")

        return result

    except Exception as e:
        error_msg = f"Failed to execute fill_read_model_for_product_task: {str(e)}"
        logger.set_code(None)
        logger.exception(e)
        return {"success": False, "product_id": product_id, "error": error_msg}


@shared_task(queue="matrix_pull", bind=True, max_retries=3, default_retry_delay=30)
def flush_pending_matrix_sync(self):
    """Read pending SKUs from Redis, dispatch rebuild tasks."""
    from django.conf import settings as django_settings

    logger = ProcessLogger("matrix.signal_sync")
    logger.set_code(5320)

    batch_threshold = getattr(django_settings, "PIM_MATRIX_SIGNALS_BATCH_THRESHOLD", 500)

    try:
        redis_client = caches["default"].client.get_client()
    except Exception as exc:
        logger.set_code(5329)
        logger.error(f"Redis unavailable during flush: {exc}")
        raise self.retry(exc=exc) from exc

    pending_key = PENDING_KEY
    lock_key = LOCK_KEY

    try:
        pipe = redis_client.pipeline()
        pipe.zrangebyscore(pending_key, "-inf", "+inf")
        pipe.delete(pending_key)
        results = pipe.execute()
        members = results[0]

        redis_client.delete(lock_key)

        redis_client.set(LAST_FLUSH_KEY, str(time.time()), ex=86400)

        if not members:
            logger.info("No pending SKUs to flush")
            return {"success": True, "flushed": 0}

        channel_skus: dict[str, list[str]] = {}
        for member in members:
            if isinstance(member, bytes):
                member = member.decode("utf-8")
            parts = member.rsplit(":", 1)
            if len(parts) != 2:
                continue
            sku, channel_idx = parts
            channel_skus.setdefault(channel_idx, []).append(sku)

        total_dispatched = 0
        for channel_idx, skus in channel_skus.items():
            has_channel_rebuild = CHANNEL_REBUILD_SENTINEL in skus
            sku_count = len([s for s in skus if s != CHANNEL_REBUILD_SENTINEL])

            if has_channel_rebuild or sku_count > batch_threshold:
                fill_read_model_for_channel_task.delay(channel_idx)
                logger.info(
                    f"Channel rebuild dispatched for channel={channel_idx} "
                    f"(count={sku_count}, threshold_exceeded={sku_count > batch_threshold}, "
                    f"explicit_rebuild={has_channel_rebuild})"
                )
                total_dispatched += 1
            else:
                for sku in skus:
                    if sku == CHANNEL_REBUILD_SENTINEL:
                        continue
                    fill_read_model_for_product_task.delay(product_id=sku, channel_idx=channel_idx)
                    total_dispatched += 1
                logger.info(f"Per-product sync dispatched for channel={channel_idx}: {sku_count} SKUs")

        logger.info(f"Flush complete: {len(members)} pending entries, {total_dispatched} tasks dispatched")
        return {
            "success": True,
            "flushed": len(members),
            "tasks_dispatched": total_dispatched,
        }

    except Exception as exc:
        logger.set_code(5329)
        logger.error(f"Flush failed: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(queue="matrix_pull")
def fill_read_model_for_channel_task(channel_idx: str):
    """Full channel rebuild — used when batch threshold exceeded."""
    logger = ProcessLogger("matrix.signal_sync")
    logger.set_code(5320)
    logger.add_log_param("channel_idx", channel_idx)

    try:
        logger.info(f"Starting full channel rebuild for channel={channel_idx}")
        result = fill_read_model_with_flags(channel_idx=channel_idx, logger=logger)

        if result["success"]:
            logger.info(f"Channel rebuild complete for channel={channel_idx}")
        else:
            logger.error(f"Channel rebuild failed for channel={channel_idx}: {result.get('error')}")

        return result

    except Exception as e:
        logger.set_code(5329)
        logger.exception(e)
        return {"success": False, "channel_idx": channel_idx, "error": str(e)}
