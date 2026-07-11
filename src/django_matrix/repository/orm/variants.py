# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_pim.models import Feature, FeatureInFeatureSet, FrontendInputType
from django_regional.models import Country, Currency, Language
from django_utils.api.exceptions import BadRequest

from django_matrix.dto.view.variants import (
    AdditionalData,
    Option,
    OptionValue,
    Variant,
    VariantAttribute,
)
from django_matrix.enums import FeatureType, ProductType
from django_matrix.models import Channel, ProductRepresentation
from django_matrix.settings import VARIANTS_ADDITIONAL_DATA
from django_matrix.utils.params import VariantsQuery


class Variants:
    channel: Channel
    language: Language
    country: Country
    currency: Currency
    throw_api_view_errors_flag: bool
    attribute_extension_cache: dict | None = None

    def __init__(self, channel, language, country, currency):
        self.channel = channel
        self.language = language
        self.country = country
        self.currency = currency
        self.throw_api_view_errors_flag = False

    def throw_api_view_errors(self, flag: bool) -> "Variants":
        self.throw_api_view_errors_flag = flag
        return self

    def get_language_iso(self):
        return self.language.iso2.lower()

    def find_by_api_query(self, params: VariantsQuery):
        parent = ProductRepresentation.objects.filter(
            channel=self.channel, product_type=ProductType.PRODUCT_CONFIGURABLE, url_keys__contains=params.url_key
        ).first()
        if not parent:
            if self.throw_api_view_errors_flag:
                raise BadRequest(f"Product {params.url_key} not found")
            else:
                raise ValueError(f"Product {params.url_key} not found")

        feature_set_idx = parent.feature_set["idx"] if "idx" in parent.feature_set else None
        filtered_query = {
            "channel": self.channel,
            "parent": parent,
            # "attributes__feature_type__in": [FeatureType.SELECT.value, FeatureType.MULTISELECT.value],
        }
        if params.on_stock is not None:
            filtered_query["on_stock"] = params.on_stock

        products = (
            ProductRepresentation.objects.filter(**filtered_query)
            .prefetch_related("attributes")
            .iterator(chunk_size=100)
        )

        return products, feature_set_idx, []

    def resolve_options(self, products, feature_set_idx):
        features_idx = []
        available_attributes = []

        # Find all features from products
        for product in products:
            for attribute in product.attributes.all():
                if attribute.feature_type not in [FeatureType.SELECT.value, FeatureType.MULTISELECT.value]:
                    continue
                if attribute.linking is False:
                    continue
                if attribute.feature_idx not in features_idx:
                    features_idx.append(attribute.feature_idx)
                if attribute.attribute_idx not in available_attributes:
                    available_attributes.append(attribute.attribute_idx)

        # Get position of all features
        positions = {}
        if feature_set_idx is not None:
            fifs = FeatureInFeatureSet.objects.filter(feature_set__idx=feature_set_idx, feature__idx__in=features_idx)
            positions = {fif.feature.idx: fif.position for fif in fifs}

        # Build options
        options = []
        features = Feature.objects.filter(idx__in=features_idx).prefetch_related("attributes")
        self.attribute_extension_cache = {}
        for feature in features:
            option = Option(
                idx=feature.idx,
                label=feature.name_lang(self.get_language_iso()),
                widget_type=FrontendInputType.labelFromId(feature.frontend_input_type),
                widget_behaviour="picker",
                position=(
                    positions[feature.idx]
                    if feature_set_idx is not None and feature.idx in positions
                    else feature.display_order
                ),
                extra_value=(
                    feature.get_extra_value_lang(self.get_language_iso())
                    if hasattr(feature, "get_extra_value_lang")
                    else feature.extra_value
                    if hasattr(feature, "extra_value")
                    else {}
                ),
                options=[],
            )
            for attribute in feature.attributes.all():
                # Aktualnie pokazujemy tylko atrybuty, które są w produktach simple szukanego configa
                if attribute.idx not in available_attributes:
                    continue
                ov = OptionValue(
                    value=attribute.idx,
                    label=attribute.name_lang(self.get_language_iso()),
                    position=attribute.display_order,
                    extension=attribute.extension,
                )
                self.attribute_extension_cache[attribute.idx] = attribute.extension
                option.options.append(ov)
            option.options.sort(key=lambda x: x.position)
            options.append(option)

        options.sort(key=lambda x: x.position)

        return options, []

    def resolve_products(self, products):
        variants = []
        for product in products:
            variant = Variant(sku=product.sku, on_stock=product.on_stock, additional_data=[], attributes=[])
            for attribute in product.attributes.all():
                if (
                    attribute.feature_type in [FeatureType.SELECT.value, FeatureType.MULTISELECT.value]
                    and attribute.linking is True
                ):
                    va = VariantAttribute(
                        feature_idx=attribute.feature_idx,
                        feature_label=attribute.feature_name_t9n.get(self.get_language_iso()),
                        value_idx=attribute.attribute_idx,
                        value_label=attribute.attribute_value(self.get_language_iso()),
                        extension=self.attribute_extension_cache.get(attribute.attribute_idx),
                    )
                    variant.attributes.append(va)
                elif attribute.feature_idx in VARIANTS_ADDITIONAL_DATA:
                    ad = AdditionalData(
                        feature_idx=attribute.feature_idx,
                        feature_label=attribute.feature_name_t9n.get(self.get_language_iso()),
                        value=attribute.attribute_value(self.get_language_iso()),
                    )
                    variant.additional_data.append(ad)
            variants.append(variant)
        return variants, []
