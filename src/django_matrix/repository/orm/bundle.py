# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_pim.models import ProductBundle
from django_pim.models.product_bundle.bundle_link import BundleLink


def get_bundle_limits(sku_list: list) -> dict:
    limits = {}
    for bundle in ProductBundle.objects.filter(real_product__sku__in=sku_list).select_related("real_product"):
        sku = bundle.real_product.sku
        entry = {}
        raw_max = bundle.get_max_limit_bundle()
        if raw_max is not None:
            try:
                entry["max_limit"] = int(raw_max)
            except (ValueError, TypeError):
                pass
        raw_min = bundle.get_min_limit_bundle()
        if raw_min is not None:
            try:
                entry["min_limit"] = int(raw_min)
            except (ValueError, TypeError):
                pass
        limits[sku] = entry
    return limits


def get_bundle_links(sku_list: list) -> dict:
    links = (
        BundleLink.objects.filter(product_bundle__real_product__sku__in=sku_list)
        .select_related("product_bundle__real_product", "subproduct__real_product")
        .values(
            "product_bundle__real_product__sku",
            "subproduct__real_product__sku",
            "quantity",
            "is_required",
            "is_default",
            "can_change_quantity",
        )
    )
    result = {}
    for link in links:
        bundle_sku = link["product_bundle__real_product__sku"]
        sub_sku = link["subproduct__real_product__sku"]
        result.setdefault(bundle_sku, {})[sub_sku] = {
            "quantity": link["quantity"],
            "is_required": link["is_required"],
            "is_default": link["is_default"],
            "can_change_quantity": link["can_change_quantity"],
        }
    return result
