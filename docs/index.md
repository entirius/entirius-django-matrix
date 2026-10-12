---
title: Matrix
description: Read-optimized product data layer. Aggregates PIM, Price Manager, and QMS into a denormalized model for fast storefront queries.
sidebar:
  label: Overview
  collapsed: true
---

`django-matrix` is the read-optimized product data layer for the Volkanos storefront. It aggregates data from PIM, Price Manager, and QMS into denormalized read model tables optimized for fast storefront API queries. All data access uses raw SQL — no ORM at query time.

## Key Concepts

### Read Model Pattern

The read model is a set of denormalized tables that hold pre-aggregated product data. They are never written to directly by the storefront. Instead, `fill-read-model` pulls from source modules (PIM, Price Manager, QMS) and writes to these tables. Reads are fast; writes happen on demand or via Celery.

### Channel Scoping

All products in the read model are scoped to a `Channel`. A channel configures which features are filterable, sortable, searchable, and visible. The same SKU can exist in multiple channels with different attribute visibility rules.

### Product Types

| Type | Description |
|------|-------------|
| `SIMPLE` | Standalone product with its own price and stock |
| `CONFIGURABLE` | Parent product with child SIMPLE variants (e.g., color/size) |
| `BUNDLE` | A group of components with selection options and per-component prices |
| `CUSTOM` | Custom product type for non-standard use cases |
| `BASE` | Internal base type; not used in storefront directly |

### Feature Restrictions

Each channel has four feature restriction tables:

| Table | Controls |
|-------|---------|
| `FilterableFeatures` | Which attributes appear as filter options |
| `SortableFeatures` | Which attributes can be used for sorting |
| `SearchableFeatures` | Which attribute values are indexed in the `search` field |
| `VisibilityFeatures` | Which attributes are returned in product responses |

### Read Model Build Flow

```
fill-read-model
  → products_and_attributes  (PIM → ProductRepresentation, Attribute, ProductT9N)
  → prices                   (Price Manager → ProductPrice)
  → on_stock                 (QMS → ProductRepresentation.on_stock)
  → pictures                 (PIM → ProductRepresentation.pictures, ProductT9N.pictures)
  → videos                   (PIM → ProductRepresentation.videos, ProductT9N.videos)
```

Run all steps or target individual steps via flags. Supports per-channel and per-SKU scope.

## API Endpoints

URL prefix: `api/matrix/<version>/<channel_idx>/`

### Products

| Endpoint | Description |
|----------|-------------|
| `GET products/` | Product listing with filtering, sorting, search, and pagination |
| `GET products/<url_key>/` | Product detail by URL key |
| `GET products/<url_key>/variants/` | Configurable product variant options and children |
| `GET bundle-config/` | Bundle product structure with sub-items, options, and prices |
| `GET prices-bundle/` | Bundle component prices (flat list, `?sku=`) |
| `GET products-categories/` | Products grouped by category |

### Prices

| Endpoint | Description |
|----------|-------------|
| `GET prices/` | Price listing for multiple SKUs (`?skus=sku1,sku2` or `?url_keys=`) |
| `GET prices/<url_key>/` | Price detail by URL key |

### Attributes

| Endpoint | Description |
|----------|-------------|
| `GET attributes/` | Attribute listing for the current product context |
| `GET attributes/<feature_type>/` | Attributes filtered by feature type |

### Search

| Endpoint | Description |
|----------|-------------|
| `GET products_m2/` | Full-text product search (Magento2-compatible) |
| `GET suggest_m2/` | Search suggestions / autocomplete |

### Filters and Options

| Endpoint | Description |
|----------|-------------|
| `GET options/` | Filter and sort options metadata (filterable features + order-by config) |

### Categories

| Endpoint | Description |
|----------|-------------|
| `GET categories/` | Category listing for the channel — filter by `depth`, `language`, `url_key`, `parent_url_key` |

Returns PIM categories directly (same source as Cynthia categories). No pagination — returns the full list for the channel. Replaces the Cynthia categories endpoint for new projects (React storefront).

### URL Maps

| Endpoint | Description |
|----------|-------------|
| `GET product/urls/` | URL key → SKU map for all products |
| `GET category/urls/` | URL key → category map for all categories |

Both URL map endpoints also have a channel-agnostic variant under `api/matrix/<version>/` (no channel in path).

### Custom Products

| Endpoint | Description |
|----------|-------------|
| `GET custom_details/` | Custom product details (`?sku=`) |
| `GET custom_attributes/` | Custom product attributes (`?sku=`) |

## Source Modules

| Source | Data provided |
|--------|--------------|
| `django-pim` | Products, attributes, features, images, videos, bundle/configurable links |
| `django-pricemanager` | Prices, special prices, tax, omnibus prices |
| `django-qms` | Stock quantities and on-stock status |
| `django-checkout` | Bundle component links (for bundle config endpoint) |
| `django-regional` | Language, currency, country models |

## Celery Integration

The `fill_read_model_for_product_task` task (queue: `matrix_pull`) rebuilds the read model for a single SKU after PIM changes are detected via journal log processing.

```bash
# Dedicated worker for single-product updates
celery -A main worker -Q matrix_pull -l error
```

## Signal-Driven Sync

Matrix can be automatically synced from PIM changes via the signal-driven sync pattern. Two Celery tasks support this:
- `flush_pending_matrix_sync` — reads debounced SKU set from Redis, dispatches rebuilds
- `fill_read_model_for_channel_task` — full channel rebuild (when batch threshold exceeded)

Both run on the `matrix_pull` queue. See [Signal-Driven Sync](/architecture/signal-driven-sync/) for full architecture.

## Pages

- [Bundle Config API](./bundle-config/) — endpoint reference for bundle product selector
- [Configuration](./configuration/) — all ~30 settings with descriptions and defaults
- [Commands](./commands/) — management commands for read model maintenance
- [Log Codes](./log-codes/) — error, warning, and info codes emitted during read model builds
- [Changelog](./changelog/) — release history
- [Database Diagrams](./erd/) — auto-generated ER diagrams
