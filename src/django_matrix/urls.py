# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import include, path

# as_view
from django.views.decorators.cache import cache_page

from django_matrix import settings
from django_matrix.settings import LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX
from django_matrix.views.attributes.extended_listing import (
    attributes_extended_listing_view,
)
from django_matrix.views.attributes.listing import attributes_listing_view
from django_matrix.views.categories.listing import categories_listing_view
from django_matrix.views.categories.urls import category_urls_view
from django_matrix.views.custom.custom_attributes import get_custom_attributes
from django_matrix.views.custom.custom_details import get_custom_details
from django_matrix.views.options.listing import options_listing_view
from django_matrix.views.prices.bundle import prices_bundle_view
from django_matrix.views.prices.details import prices_details_view
from django_matrix.views.prices.listing import prices_listing_view
from django_matrix.views.products.bundle import bundle_config_view
from django_matrix.views.products.categories import products_categories_view
from django_matrix.views.products.details import products_details_view
from django_matrix.views.products.listing import products_listing_view
from django_matrix.views.products.urls import product_urls_view
from django_matrix.views.products.variants import products_variants_view
from django_matrix.views.search.listing import search_listing_view
from django_matrix.views.search.suggest import suggest_listing_view
from django_matrix.views.stock.listing import stock_details_view, stock_listing_view


def apply_cache(view, custom_cache_ttl=None):
    endpoint_name = view.__name__
    cache_ttl = custom_cache_ttl if custom_cache_ttl else settings.CACHE_TTL
    return (
        cache_page(cache_ttl)(view)
        if all(
            [
                not any(endpoint_name.startswith(endpoint) for endpoint in LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX),
                settings.USE_CACHED_VIEWS,
                type(settings.CACHE_TTL) == int,
            ]
        )
        else view
    )


api_paths = [
    path("products_m2/", apply_cache(search_listing_view), name="product-m2-search-listing"),
    path("suggest_m2/", apply_cache(suggest_listing_view), name="product-m2-suggest-listing"),
    path("products/", apply_cache(products_listing_view), name="matrix-products-listing"),
    path("product/urls/", apply_cache(product_urls_view), name="matrix-products-urls"),
    path("category/urls/", apply_cache(category_urls_view), name="matrix-categories-urls"),
    path("products/<str:url_key>/", apply_cache(products_details_view), name="matrix-products-details"),
    path("prices/", apply_cache(prices_listing_view), name="matrix-prices-listing"),
    path("prices-bundle/", apply_cache(prices_bundle_view), name="matrix-prices-bundle"),
    path("bundle-config/", apply_cache(bundle_config_view), name="matrix-bundle-config"),
    path("prices/<str:url_key>/", apply_cache(prices_details_view), name="matrix-prices-details"),
    path("attributes/", apply_cache(attributes_listing_view), name="matrix-attributes-listing"),
    path("custom_details/", apply_cache(get_custom_details), name="matrix-custom-details"),
    path("custom_attributes/", apply_cache(get_custom_attributes), name="matrix-custom-attributes"),
    path(
        "attributes/<str:feature_type>/",
        apply_cache(attributes_extended_listing_view),
        name="matrix-attributes-extended-listing",
    ),
    path("options/", apply_cache(options_listing_view), name="matrix-options-listing"),
    path("products/<str:url_key>/variants/", apply_cache(products_variants_view), name="matrix-products-variants"),
    path("products-categories/", apply_cache(products_categories_view), name="matrix-products-categories"),
    path("categories/", apply_cache(categories_listing_view), name="matrix-categories-listing"),
    path("stock/", stock_listing_view, name="matrix-stock-listing"),
    path("stock/<path:sku>/", stock_details_view, name="matrix-stock-details"),
]

api_paths_no_channel = [
    path("product/urls/", apply_cache(product_urls_view), name="matrix-products-urls-no-channel"),
    path("category/urls/", apply_cache(category_urls_view), name="matrix-categories-urls-no-channel"),
]


urlpatterns = [
    # v2 endpoints (must be before v1 — v1's <str:version> would match "v2")
    path(f"{settings.BASE_URL}/matrix/v2/<str:channel_idx>/", include("django_matrix.api.v2.urls")),
    # v1 endpoints (unchanged)
    path(f"{settings.BASE_URL}/matrix/<str:version>/<str:channel_idx>/", include(api_paths)),
    path(f"{settings.BASE_URL}/matrix/<str:version>/", include(api_paths_no_channel)),
]
