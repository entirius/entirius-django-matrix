# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

# This attributes will be added to product read model
# You can't add more without implementing it, but u can substract some if your volkanos not using it
PRODUCT_ADDITIONAL_ATTRIBUTES = getattr(
    settings, "PRODUCT_ADDITIONAL_ATTRIBUTES", ["badge", "subname1", "subname2", "brand"]
)

# 0 - Pages of query will not be counted
# 1 - Only Next X pages will be checked if existed. X is from PAGINATION_NEXT_PAGES_COUNT variable
# 2 - Full count of pages (may slow down result on big database)
PAGINATION_TYPE = getattr(settings, "PAGINATION_TYPE", 1)
PAGINATION_NEXT_PAGES_COUNT = getattr(settings, "PAGINATION_NEXT_PAGES_COUNT", 5)
PAGINATION_MAX_RESULTS_COUNT = getattr(settings, "PAGINATION_MAX_RESULTS_COUNT", 100)
PAGINATION_DEFAULT_RESULTS_COUNT = getattr(settings, "PAGINATION_DEFAULT_RESULTS_COUNT", 12)

MATRIX_PRODUCTS_PARALLEL_QUERIES = getattr(settings, "MATRIX_PRODUCTS_PARALLEL_QUERIES", True)
# Saving net or gross price into product representation (NET/GROSS)
PRICE_TYPE = getattr(settings, "PRICE_TYPE", "GROSS")
# How much numbers after coma
PRICE_DECIMAL_PLACES = getattr(settings, "PRICE_DECIMAL_PLACES", ".01")


MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT = getattr(
    settings,
    "MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT",
    {"pr.sku": "A", "pt.name": "B", "pr.search": "C", "pt.subnames": "C", "pr.tags": "D"},
)

# This setting determines the base part of urls
# for details go see urls.py
BASE_URL = getattr(settings, "API_BASE_URL", "api").strip("/")

# Use Cashe for views (API) Default ON/OFF: OFF, Default TTL: 15 min
USE_CACHED_VIEWS = getattr(settings, "USE_CACHED_VIEWS", False)
CACHE_TTL = getattr(settings, "CACHE_TTL", 60 * 15)

# This setting is used for search engine (search based on magento2)
MAGENTO_URL = getattr(settings, "MAGENTO2_URL_FOR_CHECKOUT_EXPORT", None)
MAGENTO_TOKEN = getattr(settings, "MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT", None)

# This setting set to #20366 :
# True determines that /products/?query={"color": ["black", "red"]} will return only products with both colors
# False determines that /products/?query={"color": ["black", "red"]} will return products with black or red color
FEATURES_FILTERING_WORK_LIKE_AND_GATE = getattr(settings, "FEATURES_FILTERING_WORK_LIKE_AND_GATE", False)

# This setting determines which text features will be imported to search field
SEARCH_LIST_OF_FEATURES_IDX_MATRIX = getattr(settings, "SEARCH_LIST_OF_FEATURES_IDX_MATRIX", [])


# Settings for magento autocomplete extend #20463
MAGENTO_BASIC_AUTH_LOGIN = getattr(settings, "MAGENTO_BASIC_AUTH_LOGIN", [])
MAGENTO_BASIC_AUTH_PASSWORD = getattr(settings, "MAGENTO_BASIC_AUTH_PASSWORD", [])

# This setting determines if price tuner module is being used in matrix
USE_PRICE_TUNER_IN_MATRIX = getattr(settings, "USE_PRICE_TUNER_IN_MATRIX", False)

# This setting determines which endpoints won't be cached. You can choose from:
# [
#     "attributes_extended_listing",
#     "attributes_listing",
#     "prices_details",
#     "prices_listing",
#     "products_details",
#     "products_listing",
#     "search_listing",
#     "suggest_listing",
# ]
LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX = getattr(settings, "LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX", [])

APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES = getattr(
    settings, "APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES", True
)

MATRIX_FULL_TEXT_SEARCH = getattr(settings, "MATRIX_FULL_TEXT_SEARCH", False)
MATRIX_FULL_TEXT_LANG_SEARCH = getattr(settings, "MATRIX_FULL_TEXT_LANG_SEARCH", True)

# Requires pg_trgm PostgreSQL extension: CREATE EXTENSION IF NOT EXISTS pg_trgm;
MATRIX_FUZZY_SEARCH = getattr(settings, "MATRIX_FUZZY_SEARCH", False)
MATRIX_FUZZY_SEARCH_THRESHOLD = getattr(settings, "MATRIX_FUZZY_SEARCH_THRESHOLD", 0.35)

# Default sort applied when search is active but no explicit sort provided by the client.
# Applied AFTER search_rank as a tie-breaker. search_rank (FTS weights) stays primary.
# Format: {"feature_idx": "DESC"} or {"system_field": "ASC"} or None (disabled)
MATRIX_SEARCH_DEFAULT_SORT = getattr(settings, "MATRIX_SEARCH_DEFAULT_SORT", None)

VARIANTS_ADDITIONAL_DATA = getattr(settings, "VARIANTS_ADDITIONAL_DATA", [])

# more about thumb mechanism in django_pim
THUMBS_CONFIG = getattr(settings, "THUMBS_CONFIG", None)

# This setting determines how to import images for all languages
# 1 - Import images for all languages 1:1 from pim to product t9n
# 2 - Import images from pim, but if image in specific type is not found for language, use default language image or first found

LANGUAGE_IMAGE_IMPORT_TYPE = getattr(settings, "LANGUAGE_IMAGE_IMPORT_TYPE", 1)
LANGUAGE_VIDEO_IMPORT_TYPE = getattr(settings, "LANGUAGE_VIDEO_IMPORT_TYPE", 1)

# Datetime format to frontend
MATRIX_DATETIME_FORMAT = getattr(settings, "MATRIX_DATETIME_FORMAT", "%Y-%m-%dT%H:%M:%S%z")

# This is for visibility mechanism
# 1 - Get all features from visibilityfeatures table per channel (default)
# 2 - Get all features with omission BLACKLISTED_FEATURES_IDX_VISIBLITY

VISIBILITY_MECHANISM = getattr(settings, "VISIBILITY_MECHANISM", 1)
BLACKLISTED_FEATURES_IDX_VISIBILITY = getattr(settings, "BLACKLISTED_FEATURES_IDX_VISIBILITY", [])

# Order attributes by the per-channel `position` of the visibility feature instead of the global
# django_pim_feature.display_order. Off by default — display_order stays the source of order.
MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION = getattr(settings, "MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION", False)

DEFAULT_OPTIONS_META_DATA = {
    "order_by": {
        "idx": "order_by",
        "label": {"pl": "Sortuj według", "en": "Order by", "de": "Sortieren nach", "fr": "Trier par"},
        "type": "select",
        "position": 0,
        "options": {
            "created_at": {
                "idx": "created_at",
                "label": {"pl": "Data dodania", "en": "Added at", "de": "Hinzugefügt am", "fr": "Ajouté le"},
            },
            "price": {
                "idx": "price",
                "label": {"pl": "Cena", "en": "Price", "de": "Preis", "fr": "Prix"},
                "position": 0,
            },
        },
    },
    "filter_by": {
        "idx": "filter_by",
        "label": {"pl": "Filtruj według", "en": "Filter by", "de": "Filtern nach", "fr": "Filtrer par"},
        "type": "select",
        "options": {
            "price": {
                "idx": "price",
                "label": {"pl": "Cena", "en": "Price", "de": "Preis", "fr": "Prix"},
                "position": 0,
            }
        },
    },
}


OPTIONS_META_DATA = getattr(settings, "OPTIONS_META_DATA", DEFAULT_OPTIONS_META_DATA)

LIST_OF_BLACKLISTED_CATEGORIES_IDX_IN_VIEW = getattr(settings, "LIST_OF_BLACKLISTED_CATEGORIES_IDX_IN_VIEW", [])
BREADCRUMBS_WITHOUT_ROOT_CATEGORY_IN_VIEW = getattr(settings, "BREADCRUMBS_WITHOUT_ROOT_CATEGORY_IN_VIEW", True)

BOOL_NAME_TRANSLATION = getattr(
    settings,
    "BOOL_NAME_TRANSLATION",
    {
        True: {"pl": "Tak", "en": "Yes", "fr": "Oui", "de": "Ja"},
        False: {"pl": "Nie", "en": "No", "fr": "Non", "de": "Nein"},
    },
)

DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR = getattr(settings, "DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR", 0.3)

# Real-time stock update via signal from django_checkout
# When enabled, ProductRepresentation.stock_qty is updated immediately when stock changes in django_checkout
#
# Recommended settings by database size:
# - < 50k products:   True  (real-time updates work well)
# - 50k-100k:         True  (acceptable performance)
# - 100k+:            False
#
# When disabled, stock is updated only by batch worker
MATRIX_ENABLE_REALTIME_STOCK_UPDATE = getattr(settings, "MATRIX_ENABLE_REALTIME_STOCK_UPDATE", False)
