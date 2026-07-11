# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import hashlib
import json

from django.db import models

from django_matrix.enums import FeatureType
from django_matrix.models.base_model_abstract import BaseModel


class Attribute(BaseModel):
    product = models.ForeignKey(
        "ProductRepresentation", db_index=True, on_delete=models.CASCADE, related_name="attributes", null=False
    )
    hash = models.CharField(max_length=32, db_index=True, null=False, blank=False)
    feature_idx = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    feature_name_t9n = models.JSONField(null=True, blank=True)
    feature_type = models.CharField(
        max_length=20, choices=FeatureType.choices, db_index=True, blank=False, null=False, default=FeatureType.UNKNOWN
    )
    feature_is_for_customization = models.BooleanField(default=False, null=True, blank=True)
    attribute_idx = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    attribute_value_text = models.TextField(db_index=True, null=True, blank=True)
    attribute_value_t9n = models.JSONField(null=True, blank=True)
    attribute_value_json = models.JSONField(null=True, blank=True)
    extension = models.JSONField(null=True, blank=True)
    linking = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    # v2 flag columns — copied from PIM Feature by worker
    is_visible = models.BooleanField(default=True)
    has_visual_asset = models.BooleanField(default=False)
    is_comparable = models.BooleanField(default=False)
    is_seo = models.BooleanField(default=False)

    # Attribute group — from PIM FeatureInFeatureSet.attributes_group
    group_idx = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    group_name_t9n = models.JSONField(null=True, blank=True)
    group_position = models.IntegerField(null=True, blank=True)

    objects = models.Manager()

    def __str__(self):
        return f"f7e: {self.feature_idx} | a9e_type: {self.feature_type}{f' | a9e: {self.attribute_idx}' if self.attribute_idx else ''}"

    class Meta:
        verbose_name_plural = "Attributes"
        constraints = [models.UniqueConstraint(fields=["product", "hash"], name="unique_product_hash")]
        indexes = [
            models.Index(fields=["product"], name="idx_attr_visible", condition=models.Q(is_visible=True)),
            models.Index(fields=["product"], name="idx_attr_visual_asset", condition=models.Q(has_visual_asset=True)),
            models.Index(fields=["product"], name="idx_attr_seo", condition=models.Q(is_seo=True)),
        ]

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = self.generate_hash()
        super().save(*args, **kwargs)

    def generate_hash(self):
        return Attribute.generate_hash_by(
            self.feature_idx,
            self.attribute_idx,
            self.attribute_value_text,
            self.attribute_value_t9n,
            self.attribute_value_json,
        )

    @staticmethod
    def generate_hash_by(feature_idx, attribute_idx, attribute_value_text, attribute_value_t9n, attribute_value_json):
        # Przygotowanie ciągu wejściowego dla MD5 na podstawie wybranych kolumn
        hash_input = f"{feature_idx}-{attribute_idx}-{attribute_value_text}"

        # Serializacja pól JSON, jeśli są niepuste
        if attribute_value_t9n:
            hash_input += f"-{json.dumps(attribute_value_t9n, sort_keys=True)}"
        if attribute_value_json:
            hash_input += f"-{json.dumps(attribute_value_json, sort_keys=True)}"

        # Generowanie MD5 z ciągu wejściowego
        return hashlib.md5(hash_input.encode("utf-8")).hexdigest()

    def attribute_value(self, locale: str | None = None):
        if self.attribute_value_text:
            return self.attribute_value_text
        if self.attribute_value_t9n:
            if locale is None:
                if self.product.channel.default_language:
                    locale = self.product.channel.default_language.iso2.lower()
                else:
                    return None
            if locale in self.attribute_value_t9n:
                return self.attribute_value_t9n[locale]
        if self.attribute_value_json:
            return self.attribute_value_json

        return None
