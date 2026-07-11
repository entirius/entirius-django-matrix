# AGENTS.md

Storefront read model — distribution `entirius-django-matrix`, Django app `django_matrix`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_matrix` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- PostgreSQL only: models use GIN indexes, full-text and trigram search — `django.contrib.postgres` in `INSTALLED_APPS`.
- Default: do not commit — git is the user's call.

## Architecture

Denormalized read model of the product catalog for storefront reads.

- **Models** (`models/`): `Channel` (FK `django_regional` Language/Currency/Country + M2M),
  `ProductRepresentation` (per-channel product projection, self-FK `parent`), `ProductT9n`
  (translations), `ProductPrice`, `Attribute` (hashed, unique per product), `MatrixSettings`, and
  channel feature through-models (visibility/filterable/sortable/searchable/full-data, FK
  `django_pim.Feature`).
- **API** (`api/`, versioned `v1`/`v2`): DRF views + drf-spectacular schema; product listing,
  options, categories, search, stock, prices. v2 prices require JWT (per-customer pricing).
- **Repository** (`repository/`): ORM and raw-SQL query builders (full-text, trigram, faceting).
- **Workers** (`workers/`): fill the read model from PIM, pricing and stock; celery tasks.
- **Signals** (`signals/`): real-time stock update from a `django_checkout` signal (guarded).
- **BI** (`bi.py`): `bievents` events.

## Integration points

- `entirius-django-pim` (**required**) — product/feature source; FK `Feature`, worker reads.
- `entirius-django-regional` (**required**) — Country/Currency/Language FKs on `Channel`.
- `entirius-py-magento2-sdk2` (**required**) — Magento search/suggest workers.
- `entirius-django-qms` (extra `qms`) — stock read when `django_checkout` absent (soft).
- `entirius-django-pricemanager` (extra `pricemanager`) — price fill (soft, degrades gracefully).
- `entirius-django-pricetuner` + `entirius-django-accounts` (extra `pricetuner`) — customer-group
  pricing behind `USE_PRICE_TUNER_IN_MATRIX` (soft).
- `django_checkout` / `django_omnibus` (Etap 5, unreleased) and `django_reviews` — soft, lazily
  imported with graceful degradation; the host service provides them when present.

## Settings Reference

All read via `getattr(settings, ...)` with defaults (see `settings.py`); no fail-fast settings.
Key toggles: `MATRIX_PRODUCTS_PARALLEL_QUERIES`, `MATRIX_FULL_TEXT_SEARCH`, `MATRIX_FUZZY_SEARCH`
(+ `_THRESHOLD`), `MATRIX_ENABLE_REALTIME_STOCK_UPDATE`, `USE_PRICE_TUNER_IN_MATRIX`,
`USE_CACHED_VIEWS` (+ `CACHE_TTL`), `PRICE_TYPE`/`PRICE_DECIMAL_PLACES`, pagination knobs,
`API_BASE_URL`, `VISIBILITY_MECHANISM`. `bi.py` reads `BI_ENVIRONMENT` / `BI_BUSINESS_UNIT` at import.
