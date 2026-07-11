# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_matrix.models import Attribute


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "feature_idx",
        "feature_name_t9n",
        "feature_type",
        "attribute_idx",
        "attribute_value_text",
        "attribute_value_t9n",
        "attribute_value_json",
        "linking",
    )
    list_filter = ["product__channel", "feature_idx", "feature_type", "linking"]
    search_fields = ("product__sku", "attribute_idx", "attribute_value_text")
    autocomplete_fields = ("product",)
