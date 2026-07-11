# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_matrix.models import ProductPrice


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = (
        "product_representation",
        "currency",
        "country",
        "price",
        "range_from",
        "range_to",
        "is_only_for_verified_user",
        "omnibus_price",
        "omnibus_price_from",
        "omnibus_price_to",
    )
    search_fields = ("product_representation__sku",)
    list_filter = ["product_representation__channel", "currency", "country"]
    autocomplete_fields = ("product_representation",)
