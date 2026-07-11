# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from django_utils.api.utils import make_media_url
from process_logger import ProcessLogger

from django_matrix.models import Channel, ProductRepresentation

try:
    from django_pim.models import ProductFile
    from django_pim.models.files import FileRoleEnum
except ImportError:
    raise Exception("django_matrix does not have access to django_pim module")

FILE_TYPE_LABELS = {
    FileRoleEnum.UNDEFINED: "undefined",
    FileRoleEnum.PICTURE: "picture",
    FileRoleEnum.PDF: "pdf",
    FileRoleEnum.DOC: "doc",
    FileRoleEnum.VIDEO: "video",
}


def fill_read_model_attachments(channel: Channel, product_id: str | None = None):
    process_logger = ProcessLogger("FILL_READ_MODEL_ATTACHMENTS")
    process_logger.add_log_param("channel_idx", channel.idx)

    query = {"product__real_product__sku": product_id} if product_id else {}
    product_files = (
        ProductFile.objects.filter(product__shop__idx=channel.idx, **query)
        .select_related("product__real_product", "file", "file__file_category")
        .order_by("product__real_product__sku")
    )
    grouped = {k: list(v) for k, v in groupby(product_files, key=lambda x: x.product.real_product.sku)}

    # Pre-fetch all PRs in one query — avoids N+1 .get() per SKU
    pr_query = {"sku": product_id} if product_id else {}
    pr_lookup = {pr.sku: pr for pr in ProductRepresentation.objects.filter(channel=channel, **pr_query)}
    all_skus = set(pr_lookup.keys())

    _save_attachments(grouped, pr_lookup, all_skus, process_logger)
    _clear_stale_attachments(all_skus, channel, process_logger)


def _save_attachments(grouped: dict, pr_lookup: dict, remaining_skus: set[str], logger: ProcessLogger) -> None:
    """Build attachment JSON per product and bulk-save to read model."""
    to_update = []
    for product_sku, pf_list in grouped.items():
        pr = pr_lookup.get(product_sku)
        if not pr:
            continue

        pr.attachments = [_build_attachment_dict(pf) for pf in pf_list]
        remaining_skus.discard(product_sku)
        to_update.append(pr)

    if to_update:
        ProductRepresentation.objects.bulk_update(to_update, fields=["attachments"], batch_size=500)
        logger.set_db_operation("UPDATE", "django_matrix", "ProductRepresentation")
        logger.set_code(2030)
        logger.info(f"Bulk-updated attachments for {len(to_update)} products.")
        logger.clear_db_operation()


def _build_attachment_dict(pf) -> dict:
    """Convert a single ProductFile into the JSON dict stored on the read model."""
    f = pf.file
    cat = f.file_category
    return {
        "file_label": f.file_label,
        "file_label_t9n": f.file_label_t9n or {},
        "original_file_name": f.original_file_name,
        "file_path": make_media_url(str(f.file)) if f.file else None,
        "file_type": FILE_TYPE_LABELS.get(f.file_type, "undefined"),
        "file_size": f.weight,
        "category_code": cat.code if cat else None,
        "category_name_t9n": cat.name_t9n if cat else {},
    }


def _clear_stale_attachments(remaining_skus: set[str], channel: Channel, logger: ProcessLogger) -> None:
    """Clear attachments from products that no longer have files — single UPDATE query."""
    if not remaining_skus:
        return
    count = (
        ProductRepresentation.objects.filter(sku__in=remaining_skus, channel=channel)
        .exclude(attachments=[])
        .exclude(attachments__isnull=True)
        .update(attachments=[])
    )
    if count:
        logger.set_code(2031)
        logger.info(f"Cleared attachments from {count} products.")
