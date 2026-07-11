# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Matrix API v2 URL patterns. Mounted alongside v1 — no breaking changes."""

from django.urls import path

from django_matrix.api.v2.views.category_views import CategoriesView
from django_matrix.api.v2.views.omnibus_views import OmnibusView
from django_matrix.api.v2.views.options_views import OptionsView
from django_matrix.api.v2.views.price_views import PricesView
from django_matrix.api.v2.views.product_views import ProductCountView, ProductsView
from django_matrix.api.v2.views.search_views import SearchView
from django_matrix.api.v2.views.stock_views import StockView

urlpatterns = [
    path("products/", ProductsView.as_view(), name="matrix-v2-products"),
    path("products/count/", ProductCountView.as_view(), name="matrix-v2-products-count"),
    path("options/", OptionsView.as_view(), name="matrix-v2-options"),
    path("search/", SearchView.as_view(), name="matrix-v2-search"),
    path("categories/", CategoriesView.as_view(), name="matrix-v2-categories"),
    path("stock/", StockView.as_view(), name="matrix-v2-stock"),
    path("prices/", PricesView.as_view(), name="matrix-v2-prices"),
    path("omnibus/", OmnibusView.as_view(), name="matrix-v2-omnibus"),
]
