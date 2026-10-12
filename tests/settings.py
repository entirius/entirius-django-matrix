# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import dj_database_url

# Postgres required (GIN indexes, full-text search, trigram). CI provides DATABASE_URL,
# locally point it at any postgres 15+.
DATABASES = {
    "default": dj_database_url.config(default="postgresql://postgres:postgres@localhost:5432/test"),
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.postgres",  # GinIndex on ProductRepresentation search/url_keys
    "rest_framework",
    "drf_spectacular",
    "django_matrix",
]

# Soft dependencies — installed in service, optional for standalone tests.
# Keep minimal: only what v2 views + models actually need at import time.
_optional_apps = [
    "django_regional",
    "django_pim",
    # 3.3.0 pulled django_pricemanager into the v1 urlconf via services/bundle_service.py.
    # tests/urls.py imports that urlconf, so the models must have an app registry entry.
    "django_pricemanager",
    # workers/fill_read_model_on_stock.py reads django_qms.output; _HAS_QMS is True only when the app is enabled.
    "django_qms",
]
for _app in _optional_apps:
    try:
        __import__(_app.split(".")[0])
        INSTALLED_APPS.append(_app)
    except ImportError:
        pass

SECRET_KEY = "test-secret-key-for-matrix-tests"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
ROOT_URLCONF = "tests.urls"

# Required by django_pim.settings
TMP_DIR = "/tmp"
T9N_DEFAULT_LANG = "en"
IS_DEFAULT_LANG_FOR_CHANNELS_FROM_PIM = True

# Required by django_accounts.settings (imported transitively)
PRIVATE_DIR = "/tmp/private"
MIGRATION_0023_MECHANISM = 1

REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"}

SPECTACULAR_SETTINGS = {
    "TITLE": "Matrix API v2",
    "VERSION": "2.0.0",
    "SCHEMA_PATH_PREFIX": r"/api/",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Parallel queries use separate DB connections that can't see test transaction data
MATRIX_PRODUCTS_PARALLEL_QUERIES = False

# Disable v1 pagination count — v2 uses has_next_page (LIMIT+1) not count_x_pages
PAGINATION_TYPE = 0

# Matrix v2 cache TTL — disabled in tests
MATRIX_V2_CACHE_TTL = {
    "products": 0,
    "products_count": 0,
    "options": 0,
    "categories": 0,
    "search": 0,
    "stock": 0,
    "omnibus": 0,
}
