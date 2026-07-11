# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_matrix.models import ProductT9N


@admin.register(ProductT9N)
class ProductT9NAdmin(admin.ModelAdmin):
    list_display = ("product_representation", "language", "name", "url_key", "meta_description", "meta_title")
    search_fields = ("product_representation__sku", "name")
    list_filter = ["product_representation__channel"]
    autocomplete_fields = ("product_representation",)
