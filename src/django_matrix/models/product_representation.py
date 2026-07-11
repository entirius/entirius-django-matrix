# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from idx_normalizator import validate_sku

from django_matrix.enums import KindOfProduct, ProductType
from django_matrix.models.base_model_abstract import BaseModel


class ProductRepresentation(BaseModel):
    sku = models.CharField(db_index=True, max_length=128, null=False)
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="products", null=False)
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        db_index=True,
        blank=False,
        null=False,
        default=ProductType.PRODUCT_SIMPLE,
    )
    kind_of_product = models.CharField(
        max_length=20,
        choices=KindOfProduct.choices,
        db_index=True,
        blank=False,
        null=False,
        default=KindOfProduct.PRODUCT_PHYSICAL,
    )
    parent = models.ForeignKey(
        "ProductRepresentation", db_index=True, on_delete=models.CASCADE, related_name="childs", null=True, blank=True
    )
    on_stock = models.BooleanField(null=False, default=False)
    stock_qty = models.IntegerField(null=True, blank=True, default=0, help_text="Available stock quantity")
    url_keys = models.JSONField(db_index=True, null=True, blank=True)
    categories_url_key = models.JSONField(db_index=True, null=True, blank=True)
    categories_position = models.JSONField(db_index=True, null=True, blank=True)
    attributes_filter = models.JSONField(null=True, blank=True)
    search = models.JSONField(null=True, blank=True)
    pictures = models.JSONField(null=True, blank=True)
    videos = models.JSONField(null=True, blank=True)
    magento_id = models.IntegerField(db_index=True, null=True, blank=True)
    feature_set = models.JSONField(null=True, blank=True)
    have_product_links = models.BooleanField(null=False, default=False)
    children = models.JSONField(db_index=True, null=True, blank=True)
    attachments = models.JSONField(null=True, blank=True)
    tags = models.JSONField(null=True, blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    number_of_reviews = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    # v2 columns — populated by worker alongside v1 fields
    is_virtual = models.BooleanField(default=False)
    main_image = models.JSONField(null=True, blank=True)
    categories_data = models.JSONField(null=True, blank=True)
    product_links = models.JSONField(null=True, blank=True)

    objects = models.Manager()

    class Meta:
        ordering = ["sku"]
        verbose_name_plural = "Products Representations"
        constraints = [UniqueConstraint(Lower("sku"), "channel", name="matrix_product_sku_unique_in_channel")]

        indexes = [
            GinIndex(fields=["search"], name="idx_product_search_gin"),
            GinIndex(fields=["tags"], name="idx_product_tags_gin"),
            GinIndex(fields=["attributes_filter"], name="idx_product_attributes_gin"),
            GinIndex(fields=["url_keys"], name="idx_product_url_keys_gin"),
            models.Index(fields=["channel"], name="idx_product_channel"),
            models.Index(fields=["channel", "on_stock"], name="idx_product_channel_stock"),
            models.Index(fields=["channel", "product_type"], name="idx_product_channel_type"),
            models.Index(
                fields=["channel"],
                name="idx_pr_channel_attrs_search",
                condition=models.Q(attributes_filter__ftr_countries__isnull=False),
            ),
        ]

    def save(self, *args, **kwargs):
        validate_sku(self.sku)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.sku
