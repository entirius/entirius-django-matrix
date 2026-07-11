# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from enum import unique

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


@unique
class ProductType(TextChoices):
    PRODUCT_BASE = "BASE", _("ProductBase")
    PRODUCT_SIMPLE = "SIMPLE", _("ProductSimple")
    PRODUCT_CONFIGURABLE = "CONFIGURABLE", _("ProductConfigurable")
    PRODUCT_BUNDLE = "BUNDLE", _("ProductBundle")
    PRODUCT_CUSTOM = "CUSTOM", _("ProductCustom")

    @staticmethod
    def map(product_class: int) -> str:
        match product_class:
            case 0:
                return ProductType.PRODUCT_BASE
            case 1:
                return ProductType.PRODUCT_SIMPLE
            case 2:
                return ProductType.PRODUCT_CONFIGURABLE
            case 3:
                return ProductType.PRODUCT_BUNDLE
            case 4:
                return ProductType.PRODUCT_CUSTOM
            case _:
                return ProductType.PRODUCT_SIMPLE


class KindOfProduct(TextChoices):
    PRODUCT_PHYSICAL = "PHYSICAL", _("ProductPhysical")
    PRODUCT_VIRTUAL = "VIRTUAL", _("ProductVirtual")

    @staticmethod
    def map(kind_of_product: int) -> str:
        match kind_of_product:
            case 0:
                return KindOfProduct.PRODUCT_PHYSICAL
            case 1:
                return KindOfProduct.PRODUCT_VIRTUAL
            case _:
                return KindOfProduct.PRODUCT_PHYSICAL


@unique
class FeatureType(TextChoices):
    UNKNOWN = "UNKNOWN", _("Unknown")
    BOOL = "BOOL", _("Bool")
    DECIMAL = "DECIMAL", _("Decimal")
    VARCHAR255 = "VARCHAR255", _("Varchar 255")
    VARCHAR255_T9N = "VARCHAR255_T9N", _("Varchar 255 t9n")
    TEXT = "TEXT", _("Text")
    TEXT_T9N = "TEXT_T9N", _("Text t9n")
    SELECT = "SELECT", _("Select")
    MULTISELECT = "MULTISELECT", _("Multiselect")
    JSON = "JSON", _("Json")
    JSON_T9N = "JSON_T9N", _("Json t9n")
    DATETIME = "DATETIME", _("Datetime")
    TEMPERATURE = "TEMPERATURE", _("Temperature")
    LENGTH = "LENGTH", _("Length")
    MASS = "MASS", _("Mass")

    @staticmethod
    def map(feature_type: int):
        match feature_type:
            case 0:
                return FeatureType.UNKNOWN
            case 1:
                return FeatureType.BOOL
            case 2:
                return FeatureType.DECIMAL
            case 3:
                return FeatureType.VARCHAR255
            case 4:
                return FeatureType.VARCHAR255_T9N
            case 5:
                return FeatureType.TEXT
            case 6:
                return FeatureType.TEXT_T9N
            case 7:
                return FeatureType.SELECT
            case 8:
                return FeatureType.MULTISELECT
            case 9:
                return FeatureType.JSON
            case 10:
                return FeatureType.DATETIME
            case 11:
                return FeatureType.JSON_T9N
            case 12:
                return FeatureType.TEMPERATURE
            case 13:
                return FeatureType.LENGTH
            case 14:
                return FeatureType.MASS
            case _:
                return FeatureType.UNKNOWN


class Attributes:
    NAME = "name"
    DESC = "description"
    SHORT_DESC = "short_description"
    URL_KEY = "url_key"
    BADGE = "badge"
    SUBNAME1 = "subname1"
    SUBNAME2 = "subname2"
    BRAND = "brand"
    META_DESCRIPTION = "meta_description"
    META_TITLE = "meta_title"
    TAGS_AUTOMATIC = "tags_automatic"
    TAGS_MANUAL = "tags_manual"


class Filtering:
    PRICE = "price"


class Sorting:
    SKU = "sku"
    NAME = "name"
    CREATED = "created"
    PRICE = "price"
    ON_STOCK = "on_stock"
    RELEVANCE = "relevance"


class PaginationType:
    NONE = 0
    X_PAGES = 1
    FULL_PAGES = 2
