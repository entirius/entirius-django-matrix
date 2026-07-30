# entirius-django-matrix

Storefront read model for Django.

`django_matrix` maintains a denormalized projection of the product catalog optimized for
storefront reads: per-channel product representations, translations, prices and stock, with
faceted search (full-text, trigram, GIN indexes) and a versioned REST API consumed by the
frontend. Worker jobs fill the read model from PIM, pricing and stock sources.

## Installation

```shell
pip install entirius-django-matrix
```

Add `django_matrix` (and `django.contrib.postgres`) to `INSTALLED_APPS`. PostgreSQL is required
(GIN indexes, full-text and trigram search). The read model attaches to `django_pim` and
`django_regional`; optional integrations are exposed as extras:

```shell
pip install "entirius-django-matrix[qms,pricemanager]"
```

## Development

```shell
uv sync --all-extras
make check test
```

Tests require PostgreSQL — point `DATABASE_URL` at any postgres 15+.
See [AGENTS.md](AGENTS.md) for architecture, settings and integration points.
