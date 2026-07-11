# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from enum import unique

from django.db import models
from django.db.models import TextChoices, UniqueConstraint
from django.utils.translation import gettext_lazy as _

from django_matrix.models.base_model_abstract import BaseModel
from django_matrix.utils.params import Query


@unique
class DefaultOrder(TextChoices):
    SKU = "sku"
    NAME = "name"
    CREATED = "created"
    PRICE = "price"
    ON_STOCK = "on_stock"


class DefaultOrderDirection(TextChoices):
    DESC = "DESC", _("Descending")
    ASC = "ASC", _("Ascending")


class Channel(BaseModel):
    idx = models.CharField(max_length=64)
    label = models.CharField(max_length=64)
    default_language = models.ForeignKey(
        "django_regional.Language", related_name="matrix_channel", on_delete=models.SET_NULL, blank=True, null=True
    )
    default_currency = models.ForeignKey(
        "django_regional.Currency", related_name="matrix_channel", on_delete=models.SET_NULL, blank=True, null=True
    )
    default_country = models.ForeignKey(
        "django_regional.Country", related_name="matrix_channel", on_delete=models.SET_NULL, blank=True, null=True
    )
    languages = models.ManyToManyField(
        "django_regional.Language", related_name="matrix_channels", verbose_name="languages", blank=True
    )
    currencies = models.ManyToManyField(
        "django_regional.Currency", related_name="matrix_channels", verbose_name="currencies", blank=True
    )
    countries = models.ManyToManyField(
        "django_regional.Country", related_name="matrix_channels", verbose_name="countries", blank=True
    )
    default_order = models.CharField(
        max_length=256, choices=DefaultOrder.choices, blank=False, null=False, default=DefaultOrder.ON_STOCK
    )
    default_order_direction = models.CharField(
        max_length=256,
        choices=DefaultOrderDirection.choices,
        blank=False,
        null=False,
        default=DefaultOrderDirection.ASC,
    )
    sku_order_numeric_sort = models.BooleanField(default=False)
    prioritize_default_order = models.BooleanField(
        default=False,
        help_text="If True, default_order takes precedence over category position sorting when using category_url_key",
    )

    objects = models.Manager()

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.label} | {self.idx}"

    def get_featuers_restrictions(self, params: Query):
        restrictions = {"filterable": [], "sortable": [], "searchable": [], "features_filter_or": []}

        if params.query and len(params.query) > 0:
            filterable_features = self.filterable_features.all().prefetch_related("feature")
            restrictions["features_filter_or"] = filterable_features.filter(is_or_filter=True).values_list(
                "feature__idx", flat=True
            )

            for obj_filter in params.query:
                if isinstance(obj_filter, dict):
                    for feature_idx in obj_filter.keys():
                        for ff in filterable_features:
                            if feature_idx == ff.feature.idx:
                                restrictions["filterable"].append(feature_idx)

        if params.range and len(params.range) > 0:
            # numeric range filters (mass/temperature/length) are gated by FilterableFeatures too
            range_filterable_features = self.filterable_features.all().prefetch_related("feature")
            for obj_filter in params.range:
                if isinstance(obj_filter, dict):
                    for feature_idx in obj_filter.keys():
                        for ff in range_filterable_features:
                            if feature_idx == ff.feature.idx:
                                restrictions["filterable"].append(feature_idx)

        if (params.sort and len(params.sort) > 0) or (params.sort_feature and len(params.sort_feature) > 0):
            sortable_features = self.sortable_features.all().prefetch_related("feature")
            sort_all = (params.sort if params.sort is not None else []) + (
                params.sort_feature if params.sort_feature is not None else []
            )
            for obj_filter in sort_all:
                if isinstance(obj_filter, dict):
                    for feature_idx in obj_filter.keys():
                        for sf in sortable_features:
                            if feature_idx == sf.feature.idx:
                                restrictions["sortable"].append(feature_idx)
        if params.search:
            searchable_features = self.searchable_features.all().prefetch_related("feature")
            for srf in searchable_features:
                restrictions["searchable"].append(srf.feature.idx)
            restrictions["searchable"].append("sku")  # hardcode sku search

        return restrictions


class VisibilityFeatures(models.Model):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="visibility_features")
    feature = models.ForeignKey("django_pim.Feature", on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Visibility Feature"
        verbose_name_plural = "Visibility Features"
        constraints = [
            UniqueConstraint(fields=["channel", "feature"], name="visibility_features_unique_channel_feature")
        ]

    def __str__(self) -> str:
        return f"{self.feature.idx} | {self.position}"


class FilterableFeatures(models.Model):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="filterable_features")
    feature = models.ForeignKey("django_pim.Feature", on_delete=models.CASCADE)
    is_or_filter = models.BooleanField(default=False)
    position = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Filterable Feature"
        verbose_name_plural = "Filterable Features"
        constraints = [
            UniqueConstraint(fields=["channel", "feature"], name="filterable_features_unique_channel_feature")
        ]

    def __str__(self) -> str:
        return f"{self.feature.idx} | {self.position}"


class SortableFeatures(models.Model):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="sortable_features")
    feature = models.ForeignKey("django_pim.Feature", on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Sortable Feature"
        verbose_name_plural = "Sortable Features"
        constraints = [UniqueConstraint(fields=["channel", "feature"], name="sortable_features_unique_channel_feature")]

    def __str__(self) -> str:
        return f"{self.feature.idx} | {self.position}"


class SearchableFeatures(models.Model):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="searchable_features")
    feature = models.ForeignKey("django_pim.Feature", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Searchable feature"
        verbose_name_plural = "Searchable features"
        constraints = [
            UniqueConstraint(fields=["channel", "feature"], name="searchable_features_unique_channel_feature")
        ]

    def __str__(self) -> str:
        return f"{self.feature.idx}"


class FullDataFeatures(models.Model):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, related_name="full_data_features")
    feature = models.ForeignKey("django_pim.Feature", on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Full Data Feature"
        verbose_name_plural = "Full Data Features"
        constraints = [
            UniqueConstraint(fields=["channel", "feature"], name="full_data_features_unique_channel_feature")
        ]

    def __str__(self) -> str:
        return f"{self.feature.idx} | {self.position}"
