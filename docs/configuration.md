---
title: Configuration
description: All settings for django-matrix, including pagination, search, caching, visibility, media, and Magento integration.
---

All settings are read from Django settings via `getattr(settings, ...)` with the defaults shown. Override any of them in your `settings_local.py` or environment-specific settings file.

## Pagination

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PAGINATION_TYPE` | `int` | `1` | `0` = no page count, `1` = check next X pages only, `2` = full `COUNT(*)` on every request. Use `1` in production — `2` is slow on large catalogs. |
| `PAGINATION_NEXT_PAGES_COUNT` | `int` | `5` | How many next pages to confirm existence of. Only applies when `PAGINATION_TYPE=1`. |
| `PAGINATION_MAX_RESULTS_COUNT` | `int` | `100` | Maximum allowed page size (`limit` query parameter cap). |
| `PAGINATION_DEFAULT_RESULTS_COUNT` | `int` | `12` | Default page size when no `limit` is specified. |

## Product

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PRODUCT_ADDITIONAL_ATTRIBUTES` | `list[str]` | `["badge", "subname1", "subname2", "brand"]` | PIM attribute idxs to include in the product read model beyond core fields. Reduce to exclude unused attributes. |
| `PRICE_TYPE` | `str` | `"GROSS"` | Whether to save `NET` or `GROSS` price into the read model. |
| `PRICE_DECIMAL_PLACES` | `str` | `".01"` | Price rounding precision string (e.g., `".01"` rounds to 2 decimal places). |
| `MATRIX_PRODUCTS_PARALLEL_QUERIES` | `bool` | `True` | Run product subqueries in parallel DB connections. Verify connection pool sizing before enabling on high-traffic deployments. |
| `VARIANTS_ADDITIONAL_DATA` | `list` | `[]` | Extra fields to include in variant responses. |
| `APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES` | `bool` | `True` | Apply special price even when the validity date range is NULL (i.e., no expiry). Set to `False` to require explicit dates. |
| `MATRIX_DATETIME_FORMAT` | `str` | `"%Y-%m-%dT%H:%M:%S%z"` | Datetime format string for all datetime fields in API responses. |

## Search

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `MATRIX_FULL_TEXT_SEARCH` | `bool` | `False` | Use Postgres full-text search (`tsvector`) instead of JSON-field search. Requires FTS index on `ProductRepresentation`. |
| `MATRIX_FULL_TEXT_LANG_SEARCH` | `bool` | `True` | Use language-aware FTS dictionary (e.g., `english`, `polish`) when FTS is enabled. |
| `MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT` | `dict` | `{"pr.sku": "A", "pt.name": "B", "pr.search": "C", "pr.tags": "D"}` | FTS weight configuration per column. Higher weight letters rank matches higher. |
| `SEARCH_LIST_OF_FEATURES_IDX_MATRIX` | `list[str]` | `[]` | Feature idxs whose text values are imported into the `search` JSON field during read model fill. Used for JSON-based search. |

## Cache

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `USE_CACHED_VIEWS` | `bool` | `False` | Enable Django `cache_page` on all API views. Requires a working Django cache backend. |
| `CACHE_TTL` | `int` | `900` | Cache TTL in seconds (default: 15 minutes). Must be an integer — non-integer values disable caching. |
| `LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX` | `list[str]` | `[]` | View function name prefixes to exclude from caching even when `USE_CACHED_VIEWS=True`. Valid values: `"attributes_extended_listing"`, `"attributes_listing"`, `"prices_details"`, `"prices_listing"`, `"products_details"`, `"products_listing"`, `"search_listing"`, `"suggest_listing"`. |

## Filtering

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `FEATURES_FILTERING_WORK_LIKE_AND_GATE` | `bool` | `False` | Controls multi-value attribute filtering. `False` = OR logic (products matching any value). `True` = AND logic (products matching all values). Example: `?query={"color": ["black", "red"]}` returns black OR red products by default; set to `True` for black AND red. |

## Visibility

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `VISIBILITY_MECHANISM` | `int` | `1` | `1` = use `VisibilityFeatures` table per channel to determine which features are returned. `2` = return all features except those in `BLACKLISTED_FEATURES_IDX_VISIBILITY`. |
| `BLACKLISTED_FEATURES_IDX_VISIBILITY` | `list[str]` | `[]` | Feature idxs to hide when `VISIBILITY_MECHANISM=2`. Has no effect when mechanism is `1`. |
| `MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION` | `bool` | `False` | Order attributes by the per-channel `position` of the visibility feature instead of the global `django_pim_feature.display_order`. Attributes with no row in the visibility table (queries filtered by `only_custom` or `feature_type` skip the visibility gate) have no position and sort last. |

## Categories

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `LIST_OF_BLACKLISTED_CATEGORIES_IDX_IN_VIEW` | `list[str]` | `[]` | Category idxs to exclude from the `products-categories` view response. |
| `BREADCRUMBS_WITHOUT_ROOT_CATEGORY_IN_VIEW` | `bool` | `True` | When `True`, strips the root category from breadcrumb arrays in responses. |
| `BOOL_NAME_TRANSLATION` | `dict` | `{True: {"pl": "Tak", "en": "Yes", ...}, ...}` | Per-language labels for boolean attribute values. Storefront reads these from the attribute response. |

## Media

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `LANGUAGE_IMAGE_IMPORT_TYPE` | `int` | `1` | `1` = import images per language 1:1 from PIM. `2` = import images from PIM but fall back to default language image if not found for a specific language. |
| `LANGUAGE_VIDEO_IMPORT_TYPE` | `int` | `1` | Same as `LANGUAGE_IMAGE_IMPORT_TYPE`, applied to videos. |
| `THUMBS_CONFIG` | `dict\|None` | `None` | Thumbnail size configuration. Mirrors `django_pim` thumb config. Set to a dict of named sizes to enable thumbnail URL generation. |

## Options Metadata

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `OPTIONS_META_DATA` | `dict` | See below | Configuration for the `options/` endpoint. Defines the `order_by` and `filter_by` select options with labels per language. Override to add or remove sort/filter options. |

Default `OPTIONS_META_DATA` includes `order_by` with `created_at` and `price` options, and `filter_by` with a `price` range option. Labels are provided in `pl`, `en`, `de`, and `fr`.

## Magento Integration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `MAGENTO2_URL_FOR_CHECKOUT_EXPORT` | `str\|None` | `None` | Magento2 REST API base URL for the `suggest_m2` autocomplete extension. Map to `MAGENTO_URL` in matrix settings. |
| `MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT` | `str\|None` | `None` | Magento2 API bearer token. Map to `MAGENTO_TOKEN` in matrix settings. |
| `MAGENTO_BASIC_AUTH_LOGIN` | `str` | `[]` | Basic auth username for Magento2 requests (used in some deployments with auth-protected Magento endpoints). |
| `MAGENTO_BASIC_AUTH_PASSWORD` | `str` | `[]` | Basic auth password for Magento2 requests. |

To use the `suggest_m2` endpoint with Magento2 as the search backend, set `MAGENTO2_URL_FOR_CHECKOUT_EXPORT` and `MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT` in Django settings. Then run `fill-products-magento-id` to populate `magento_id` on `ProductRepresentation` rows from a CSV export.

## PriceTuner

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `USE_PRICE_TUNER_IN_MATRIX` | `bool` | `False` | Enable `django-pricetuner` price adjustment layer. Requires `django-pricetuner` to be installed. |

## Safety

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR` | `float` | `0.3` | Maximum fraction of rows that can be deleted in a single bulk cleanup pass. If a fill-read-model run would delete more than this fraction of existing rows, the operation stops and logs error 4032/4033/4034. Prevents accidental data wipeout from bad imports. Raise only with explicit intent. |

## URL Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `API_BASE_URL` | `str` | `"api"` | Base URL prefix for all matrix API endpoints. Controls the URL pattern registered in `urls.py`. |
