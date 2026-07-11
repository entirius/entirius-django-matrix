# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_matrix.models import ProductRepresentation


@admin.register(ProductRepresentation)
class ProductRepresentationAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "channel",
        "product_type",
        "on_stock",
        "magento_id",
        "have_product_links",
        "kind_of_product",
        "number_of_reviews",
    )
    search_fields = ("sku", "magento_id")
    autocomplete_fields = ("parent",)
    list_filter = ["channel", "product_type", "on_stock", "have_product_links"]
