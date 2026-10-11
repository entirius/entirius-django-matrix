# AGENTS.md

Storefront read model — distribution `entirius-django-matrix`, Django app `django_matrix`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

Tests need PostgreSQL: set `DATABASE_URL` (the default in `tests/settings.py` points at a local postgres).

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_matrix` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- PostgreSQL only: models use GIN indexes, full-text and trigram search — `django.contrib.postgres` in `INSTALLED_APPS`.
- Default: do not commit — git is the user's call.

### Commit Message Format

**NEVER add `Co-Authored-By: Claude ...` (or any other Claude/Anthropic attribution) to commit messages.**

This overrides the default Claude Code behavior of appending a `Co-Authored-By` trailer. Commit messages MUST contain only the user's authored content — no robot footer, no "Generated with Claude Code" line, no co-author trailer.

Same rule applies to PR descriptions: no `Generated with [Claude Code]` footer.

## Architecture

Denormalized read model of the product catalog for storefront reads.

- **Models** (`models/`): `Channel` (FK `django_regional` Language/Currency/Country + M2M),
  `ProductRepresentation` (per-channel product projection, self-FK `parent`), `ProductT9N`
  (translations), `ProductPrice`, `Attribute` (hashed, unique per product), `MatrixSettings`, and
  channel feature through-models (visibility/filterable/sortable/searchable/full-data, FK
  `django_pim.Feature`).
- **API** (v1 in `views/` + `urls.py`, v2 in `api/v2/`): DRF views + drf-spectacular schema; product listing,
  options, categories, search, stock, prices. v2 prices require JWT (per-customer pricing).
- **Repository** (`repository/`): ORM and raw-SQL query builders (full-text, trigram, faceting).
- **Workers** (`workers/`): fill the read model from PIM, pricing and stock; celery tasks.
- **Signals** (`signals/`): real-time stock update from a `django_checkout` signal (guarded).
- **BI**: management commands are wrapped with the `bievents` command decorator.

### Integration points

- `entirius-django-pim` (**required**) — product/feature source; FK `Feature`, worker reads.
- `entirius-django-regional` (**required**) — Country/Currency/Language FKs on `Channel`.
- `entirius-py-magento2-sdk2` (**required**) — Magento search/suggest workers.
- `entirius-django-qms` (extra `qms`) — stock read when `django_checkout` absent (soft).
- `entirius-django-pricemanager` (extra `pricemanager`) — price fill (soft, degrades gracefully).
- `entirius-django-checkout` (extra `checkout`) — stock signal/model, QMS fallback (soft).
- customer-group pricing behind `USE_PRICE_TUNER_IN_MATRIX` — lazy import with graceful fallback;
  the integrating package ships outside this repository.
- `entirius-django-omnibus` (extra `omnibus`) — omnibus price lookup (soft, `None` when absent).
- `entirius-django-reviews` (extra `reviews`) — product average-rating fill (soft, `None` when absent).

| Topic | Where |
|---|---|
| Settings with defaults | `docs/configuration.md` |
| API v2 | `docs/api-v2.md` |
| Management commands | `docs/commands.md` |
| Bundle configuration | `docs/bundle-config.md` |
| Log codes | `docs/log-codes.md` |
| ERD config for the docs ERD generator | `docs/erd-config.yaml`, `docs/erd.md` |

## Settings

All read via `getattr(settings, ...)` with defaults (see `settings.py`, reference in `docs/configuration.md`); no fail-fast settings.
Key toggles: `MATRIX_PRODUCTS_PARALLEL_QUERIES`, `MATRIX_FULL_TEXT_SEARCH`, `MATRIX_FUZZY_SEARCH`
(+ `_THRESHOLD`), `MATRIX_ENABLE_REALTIME_STOCK_UPDATE`, `USE_PRICE_TUNER_IN_MATRIX`,
`USE_CACHED_VIEWS` (+ `CACHE_TTL`), `PRICE_TYPE`/`PRICE_DECIMAL_PLACES`, pagination knobs,
`API_BASE_URL`, `VISIBILITY_MECHANISM`.

## Gotchas

- The public v2 views (products, count, options, search, categories, stock, omnibus) declare
  `authentication_classes = []` and `AllowAny`: credentials are ignored there, whatever the service's DRF defaults.
  A new public view declares the same; `prices/` is the one JWT view.
- Most optional sibling imports catch `(ImportError, RuntimeError)` (`RuntimeError`: installed but not in
  `INSTALLED_APPS`); the omnibus import of `repository/orm/prices.py`, `dto/view/price.py` and
  `signals/receivers.py` still catch `ImportError` only.
