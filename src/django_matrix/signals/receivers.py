# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.dispatch import receiver
from process_logger import ProcessLogger

try:
    from django_checkout.signals.signals import stock_changed_signal
except ImportError:
    stock_changed_signal = None

from django_matrix import settings
from django_matrix.models import Channel, ProductRepresentation

_stock_receiver = receiver(stock_changed_signal) if stock_changed_signal is not None else lambda f: f


@_stock_receiver
def update_product_stock_on_stock_changed(sender, instance, sku, channel, old_quantity, new_quantity, **kwargs):
    """
    Receiver for stock_changed_signal from django_checkout.
    Updates ProductRepresentation.stock_qty and on_stock when stock changes.
    """
    if not settings.MATRIX_ENABLE_REALTIME_STOCK_UPDATE:
        return

    logger = ProcessLogger("MATRIX_STOCK_UPDATE_FROM_SIGNAL", "django_matrix")
    logger.add_log_param("sku", sku)
    logger.add_log_param("channel_idx", channel)
    logger.add_log_param("old_quantity", old_quantity)
    logger.add_log_param("new_quantity", new_quantity)

    try:
        matrix_channel = Channel.objects.filter(idx=channel).first()
        if not matrix_channel:
            logger.set_code(2016)
            logger.info(f"Channel {channel} not found in django_matrix. Skipping stock update.")
            return

        product = ProductRepresentation.objects.filter(sku=sku, channel=matrix_channel).first()
        if not product:
            logger.set_code(2017)
            logger.info(f"ProductRepresentation {sku} not found for channel {channel}. Skipping stock update.")
            return

        product.stock_qty = new_quantity
        product.on_stock = new_quantity > 0
        product.save(update_fields=["stock_qty", "on_stock"])

        logger.set_code(2018)
        logger.set_db_operation("UPDATE", "django_matrix", "ProductRepresentation")
        logger.info(
            f"ProductRepresentation stock updated: sku={sku}, channel={channel}, "
            f"qty={old_quantity}->{new_quantity}, on_stock={product.on_stock}"
        )

        if product.parent:
            parent = product.parent
            logger.add_log_param("parent_sku", parent.sku)

            children = ProductRepresentation.objects.filter(parent=parent, channel=matrix_channel)
            total_parent_qty = sum(child.stock_qty or 0 for child in children)

            parent.stock_qty = total_parent_qty
            parent.on_stock = total_parent_qty > 0
            parent.save(update_fields=["stock_qty", "on_stock"])

            logger.set_code(2019)
            logger.info(
                f"Parent ProductRepresentation stock updated: sku={parent.sku}, "
                f"total_qty={total_parent_qty}, on_stock={parent.on_stock}"
            )
            logger.delete_log_param("parent_sku")

    except Exception as e:
        logger.set_code(4029)
        logger.exception(e)
