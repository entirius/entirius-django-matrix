# entirius-django-matrix

A Django module that keeps the storefront read model of Entirius, the open-source modular ecommerce platform. It
holds a denormalized, per-channel projection of the product catalog — translations, prices and stock — and serves
it to the storefront over a versioned REST API with faceted, full-text and trigram search.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-matrix.svg)](https://pypi.org/project/entirius-django-matrix/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-matrix.svg)](https://pypi.org/project/entirius-django-matrix/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-matrix/blob/develop/LICENSE)

## What it does

- Keeps one product representation per sales channel, with translations, prices and stock.
- Serves product listings, product details, categories, options, prices and stock to the storefront.
- Searches the catalog with facets, PostgreSQL full-text search and optional trigram (fuzzy) matching.
- Fills the read model from the product, pricing and stock modules with worker jobs and management commands.
- Degrades gracefully when an optional source module (stock, prices, omnibus prices, reviews) is not installed;
  stock, prices and reviews also when the module is installed but not enabled.

## Installation

```shell
uv add entirius-django-matrix
pip install entirius-django-matrix
```

```python
INSTALLED_APPS = [
    ...
    "django.contrib.postgres",
    "django_utils",
    "django_regional",
    "django_pim",
    "django_matrix",
]

# urls.py
urlpatterns = [
    path("", include("django_matrix.urls")),
]
```

No setting is required: every setting has a default. Reference with defaults:
https://github.com/entirius/entirius-django-matrix/blob/develop/docs/configuration.md

Optional integrations are extras: `qms` (stock), `pricemanager` (prices), `checkout` (real-time stock updates),
`omnibus` (lowest recent price), `reviews` (average rating).

```shell
uv add "entirius-django-matrix[qms,pricemanager]"
```

## Quick start

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("", include("django_matrix.urls")),
]
```

```shell
python manage.py migrate
python manage.py fill-read-model
```

## Requirements

- Python 3.11 or newer, Django 5.0 or newer.
- PostgreSQL (GIN indexes, full-text search; `pg_trgm` for fuzzy search).
- Entirius packages pulled in: `entirius-django-utils`, `entirius-django-pim`, `entirius-django-regional`,
  `entirius-py-magento2-sdk2`, `entirius-py-idx-normalizator`, `entirius-py-bievents`, `entirius-py-process-logger`.

## Documentation

- Module docs: https://github.com/entirius/entirius-django-matrix/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-matrix/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos), next to the product, pricing and stock modules.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-pim, https://github.com/entirius/entirius-django-pricemanager,
  https://github.com/entirius/entirius-django-qms

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-matrix/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-matrix/blob/develop/LICENSE.
