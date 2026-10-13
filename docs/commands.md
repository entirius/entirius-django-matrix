---
title: Commands
description: Management commands for building, maintaining, and clearing the django-matrix read model.
---

## fill-read-model

Rebuilds the Matrix read model from source modules (PIM, Price Manager, QMS). Only enabled products are pulled from PIM. Without flags, runs all steps for all channels.

```bash
python manage.py fill-read-model
```

### Options

| Flag | Type | Description |
|------|------|-------------|
| `--channel_idx` | `str` | Limit to a specific channel by its `idx`. Defaults to all channels. |
| `--product_id` | `str` | Limit to a single product by SKU. Useful for quick single-product refreshes. |
| `--simple` | `bool` | Process only simple products (`product_class=1`). |
| `--config` | `bool` | Process only configurable products (`product_class=2`). |
| `--bundle` | `bool` | Process only bundle products (`product_class=3`). |
| `--custom` | `bool` | Process only custom products (`product_class=4`). |
| `--prices` | `bool` | Process prices only (from Price Manager). |
| `--onstock` | `bool` | Process stock status only (from QMS). |
| `--pictures` | `bool` | Process pictures and thumbnails only. |
| `--videos` | `bool` | Process videos only. |

When no product-type or data-type flags are specified, all steps run. When one or more flags are set, only those steps execute.

### Examples

```bash
# Full rebuild, all channels
python manage.py fill-read-model

# Rebuild single channel
python manage.py fill-read-model --channel_idx my-channel

# Refresh a single product across all channels
python manage.py fill-read-model --product_id CHAIR-001

# Refresh prices and stock only
python manage.py fill-read-model --prices --onstock

# Rebuild simple products + pictures for one channel
python manage.py fill-read-model --simple --pictures --channel_idx my-channel
```

### Processing Order

When all flags are False (default), steps execute in this order per channel:

1. Custom products (`product_class=4`)
2. Bundle products (`product_class=3`)
3. Configurable products (`product_class=2`)
4. Simple products (`product_class=1`)
5. Prices
6. Stock status
7. Pictures and thumbnails
8. Videos

The `fill_read_model_for_product_task` Celery task (queue: `matrix_pull`) runs the same logic asynchronously for individual SKU updates triggered by PIM journal processing.

### One Fill per Channel

Every product step of a fill stamps the rows it writes with its start time and ends by deleting the rows of its scope (the channel, or the one SKU) that carry an older stamp or none. A row with a newer stamp belongs to a later run and stays. So that two fills never interleave on a channel, the whole per-channel body (products, prices, stock, pictures, videos, attachments and the cleanup) runs under a PostgreSQL session advisory lock keyed by the channel (`pg_advisory_lock(0x4D58464C, <channel id>)`, `django_matrix.workers.fill_lock`). The management command and both Celery tasks take it: a second fill of the same channel waits for the first and then runs, and logs one line after 5 seconds of waiting; fills of different channels do not wait for each other. A waiting task keeps its worker process until the lock is free. The lock is released when the fill ends and disappears with the database session if the process dies. It needs a connection that stays on one PostgreSQL session for the whole fill, so it does not work through a transaction-pooling proxy between the workers and the database.

---

## cleanup-read-model

Removes `ProductRepresentation` rows for products that are disabled or no longer exist in PIM. Run after deleting or disabling products in PIM to keep the read model in sync.

```bash
python manage.py cleanup-read-model
```

### Options

| Flag | Type | Description |
|------|------|-------------|
| `--channel_idx` | `str` | Limit cleanup to a specific channel. Defaults to all channels. |

The `DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR` setting (default `0.3`) limits how many rows can be deleted in one pass. If a run would delete more than 30% of rows, it stops and logs error codes 4032–4034. See [Configuration](./configuration/) for details.

---

## clear-cache-matrix

Clears the Django view cache (`cache_page`) for Matrix API views. Only relevant when `USE_CACHED_VIEWS=True`.

```bash
python manage.py clear-cache-matrix
```

### Options

| Flag | Description |
|------|-------------|
| `--all` | Clear the entire Django cache, not just Matrix view cache. |

If the configured cache backend supports `delete_pattern` (e.g., django-redis), the command selectively deletes keys matching `*views.decorators.cache.cache_page*`. Otherwise, it clears the entire cache with a warning.

---

## fill-products-magento-id

Imports Magento product IDs into `ProductRepresentation.magento_id` from a CSV file. Used when integrating with the Magento2-based `suggest_m2` search endpoint.

```bash
python manage.py fill-products-magento-id <file_path>
```

### Arguments

| Argument | Description |
|----------|-------------|
| `file_path` | Required. Absolute path to the CSV file. |
| `--channel_idx` | Optional. Limit import to a specific channel. |

### CSV Format

```
sku,id
CHAIR-001,5481
CHAIR-002,5482
CHAIR-003,5483
```

The CSV must have `sku` and `id` columns. Rows missing an `id` value are skipped. The command prints how many IDs were imported from the total rows in the file.

After import, run `fill-read-model` to propagate changes if needed.
