# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django_pim.models import Feature, FeatureScopeEnum

from django_matrix.models import (
    Channel,
    FilterableFeatures,
    FullDataFeatures,
    SearchableFeatures,
    SortableFeatures,
    VisibilityFeatures,
)


class VisibilityFeaturesInline(admin.TabularInline):
    model = VisibilityFeatures
    ordering = ["position"]
    extra = 0
    autocomplete_fields = ["feature"]


class FiltreableFeaturesInline(admin.TabularInline):
    model = FilterableFeatures
    ordering = ["position"]
    extra = 0
    autocomplete_fields = ["feature"]


class SortableFeaturesInline(admin.TabularInline):
    model = SortableFeatures
    ordering = ["position"]
    extra = 0
    autocomplete_fields = ["feature"]


class SearchableFeaturesInline(admin.TabularInline):
    model = SearchableFeatures
    extra = 0
    autocomplete_fields = ["feature"]


class FullDataFeaturesInline(admin.TabularInline):
    model = FullDataFeatures
    ordering = ["position"]
    extra = 0
    autocomplete_fields = ["feature"]


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = (
        "idx",
        "label",
        "default_language",
        "default_currency",
        "default_country",
        "default_order",
        "default_order_direction",
        "sku_order_numeric_sort",
        "prioritize_default_order",
        "created_at",
        "modified_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "idx",
                    "label",
                    "default_language",
                    "default_currency",
                    "default_country",
                    "languages",
                    "currencies",
                    "countries",
                )
            },
        ),
        (
            "Sorting settings",
            {
                "description": "Select a sort for the product listing",
                "fields": (
                    "default_order",
                    "default_order_direction",
                    "sku_order_numeric_sort",
                    "prioritize_default_order",
                ),
            },
        ),
    )

    inlines = [
        VisibilityFeaturesInline,
        FiltreableFeaturesInline,
        SortableFeaturesInline,
        SearchableFeaturesInline,
        FullDataFeaturesInline,
    ]

    actions = [
        "copy_filterable_features",
        "clear_filterable_features",
        "copy_visible_features",
        "clear_visible_features",
        "copy_searchable_features",
        "clear_searchable_features",
        "copy_full_data_features",
        "clear_full_data_features",
    ]

    def copy_features(self, request, queryset, filter_field, model):
        for channel in queryset:
            features = Feature.objects.filter(**{filter_field: True}).exclude(scope=FeatureScopeEnum.SYSTEM)
            for feature in features:
                model.objects.create(channel=channel, feature=feature, position=feature.display_order)
        self.message_user(request, f"{model._meta.verbose_name_plural.capitalize()} copied successfully.")

    def clear_features(self, request, queryset, model):
        for channel in queryset:
            model.objects.filter(channel=channel).delete()
        self.message_user(request, f"{model._meta.verbose_name_plural.capitalize()} cleared successfully.")

    def copy_filterable_features(self, request, queryset):
        self.copy_features(request, queryset, "is_filterable", FilterableFeatures)

    copy_filterable_features.short_description = "Copy Filterable Features from django_pim"

    def clear_filterable_features(self, request, queryset):
        self.clear_features(request, queryset, FilterableFeatures)

    clear_filterable_features.short_description = "Clear Filterable Features"

    def copy_visible_features(self, request, queryset):
        self.copy_features(request, queryset, "is_visible", VisibilityFeatures)

    copy_visible_features.short_description = "Copy Visible Features from django_pim"

    def clear_visible_features(self, request, queryset):
        self.clear_features(request, queryset, VisibilityFeatures)

    clear_visible_features.short_description = "Clear Visible Features"

    def copy_searchable_features(self, request, queryset):
        self.copy_features(request, queryset, "is_searchable", SearchableFeatures)

    copy_searchable_features.short_description = "Copy Searchable Features from django_pim"

    def clear_searchable_features(self, request, queryset):
        self.clear_features(request, queryset, SearchableFeatures)

    clear_searchable_features.short_description = "Clear Searchable Features"

    def copy_full_data_features(self, request, queryset):
        self.copy_features(request, queryset, "is_visible", FullDataFeatures)

    copy_full_data_features.short_description = "Copy Full Data Features from django_pim"

    def clear_full_data_features(self, request, queryset):
        self.clear_features(request, queryset, FullDataFeatures)

    clear_full_data_features.short_description = "Clear Full Data Features"
