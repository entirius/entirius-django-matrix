# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_matrix.models.base_model_abstract import BaseModel


class ProductT9N(BaseModel):
    product_representation = models.ForeignKey(
        "ProductRepresentation", db_index=True, on_delete=models.CASCADE, related_name="t9ns", null=False
    )
    language = models.ForeignKey(
        "django_regional.Language", related_name="matrix_product_t9n", on_delete=models.SET_NULL, blank=True, null=True
    )
    name = models.CharField(max_length=1024, db_index=True, null=True, blank=True)
    desc = models.TextField(null=True, blank=True)
    short_desc = models.TextField(null=True, blank=True)
    url_key = models.CharField(max_length=1024, db_index=True, null=True, blank=True)
    badges = models.JSONField(null=True, blank=True)
    subnames = models.JSONField(null=True, blank=True)
    meta_title = models.CharField(max_length=1024, null=True, blank=True)
    meta_description = models.CharField(max_length=1024, null=True, blank=True)
    brands = models.JSONField(null=True, blank=True)
    pictures = models.JSONField(null=True, blank=True)
    videos = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    objects = models.Manager()

    class Meta:
        ordering = ["product_representation__sku"]
        verbose_name_plural = "Products T9Ns"
        constraints = [
            models.UniqueConstraint(fields=["product_representation", "language"], name="unique_product_t9n_language")
        ]

    def __str__(self):
        return self.product_representation.sku
