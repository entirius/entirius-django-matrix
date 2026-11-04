# Changelog

## Unreleased

### Fixed

- The v1 and v2 product listings no longer answer 500 with the default `PAGINATION_TYPE = 1` when the page count runs
  on the request thread: with `MATRIX_PRODUCTS_PARALLEL_QUERIES = False`, or when the parallel queries fail (for
  example "too many clients") and the listing falls back to running them in turn. The count read a page size the
  listing parameters do not carry (`KeyError: 'limit'`); it now runs the count the parallel path runs, over the whole
  listing.
- v1 `products/?magento_id=` and the Magento search listing `products_m2/` answer again; on psycopg 3 both failed
  with a 500, because the filter passed the ids as a tuple. The ids now go to Postgres as one bound integer array,
  used by the filter and by the order (products come back in the order of the ids). A value that is not a 32-bit
  integer matches no product instead of failing the query.
- v2 and v1 `stock/` (client-visible): a bundle answers what its components allow, as the cart counts it, not its
  own Stock row. A bundle with a component sold out answered its own Stock row (15 pieces in the seed), so a storefront
  let the customer add it and the cart then marked the line `out_of_stock`. The count comes from checkout
  (`output.quantities.get_bundle_quantities`); with a checkout that does not have it yet, a bundle keeps its own row
  as before. The `on_stock` read model counts bundles the same way, so a bundle with limits is no longer sold out
  over an optional component.
- `stock/` and the `on_stock` read model read the channel's global supplier, like the cart. With more than one Stock
  row per SKU they took whichever came last.
- A paginated listing no longer repeats some products and loses others. Every product query now ends its `ORDER BY`
  with `pr.id`; before, only a price sort and a category listing did, so products that tied on the default `on_stock`
  order, on `s_on_stock` or on `s_name` could land on two pages or on none, depending on the query plan. Listings
  without a category and search results were affected.
- A multi-key sort with `s_price` first honours the next key (`s_price=asc&s_name=desc`). The price sort put `pr.id`
  right after the price, so products of one price were ordered by id and the next key did nothing.
- The default `on_stock` listing reads its page from an index again, in both directions. With `pr.id` at the end of
  the `ORDER BY`, `idx_product_channel_stock (channel, on_stock)` no longer covered the order, and page 1 of a
  60k-product channel took 83 ms (a sort of the whole channel) instead of 0.1 ms. Migration `0047` builds
  `idx_product_channel_stock_id (channel, on_stock, id)`, `0048` drops the old index it makes redundant; both run
  `CONCURRENTLY`, so the table stays writable. The tie-breaker now runs in the direction of the first sort key
  (`pr.id DESC` after `on_stock DESC`), so a descending order is a backward scan of the same index. If `0047` is
  interrupted it leaves an invalid index: `DROP INDEX CONCURRENTLY idx_product_channel_stock_id;` and migrate again.
- The listing count (`PAGINATION_TYPE` 1 and 2) no longer sorts what it counts. It wrapped the whole query,
  `ORDER BY` included, so Postgres sorted every product of the listing first; on 60k products the count drops from
  25 ms (11 ms before the tie-breaker) to 5 ms.


## 4.5.0 — 2026-10-27

### Added

- `fetch_categories=true` on the v1 `products/` and `products/<url_key>/` views side-loads each product's PIM
  categories (with breadcrumbs, the shape of `products-categories/`) as `categories`, so a storefront no longer needs
  a second round trip. A SKU with no PIM product gets an empty list. Without the parameter the response is unchanged.
  The v2 views do not have it.
- `MATRIX_SORT_ATTRIBUTES_BY_CHANNEL_POSITION` (default `False`): attributes are ordered by the per-channel
  `position` of the visibility feature instead of the global `display_order`; attributes with no per-channel row sort
  last.

### Changed

- The options payload drops a numeric range whose min equals max (a category holding one product with the feature):
  a slider that cannot move filters nothing. DECIMAL ranges were already dropped in SQL.

### Fixed

- The product listing no longer leaks database connections. `execute_parallel_queries` runs the list and its COUNT in
  two pool threads; Django keeps a connection per thread and closes it when a request ends, which never happens in a
  pool thread, so every listing left two idle connections until garbage collection. Under load Postgres refused new
  clients ("too many clients already") and every API call answered 500. Each pool thread now closes its own
  connection.
- A configurable product no longer goes out of stock when only that product is refreshed. The per-product on-stock
  pass (`fill_read_model_on_stock_batch` with `product_id`, run by the PIM signal refill) read only the parent's own
  stock, so the configurable got `on_stock = false` and qty 0 while its variants were available. The pass now covers
  the product's family (the product, its parent and the parent's children); a variant's pass refreshes its parent too.

## 4.4.1 — 2026-10-13

### Fixed

- Products no longer go missing from the read model after a seed or a large import. Two fills that overlapped on one
  channel (a full channel fill and a per-product fill, or the fills of a configurable product and of its variant)
  could delete rows the other had just written: a product, its translations and attributes, and with a configurable
  parent its variants too. A fill now holds a PostgreSQL session advisory lock for its channel for all of its steps,
  so a second fill of that channel waits and then runs; fills of different channels do not wait for each other. The
  cleanup deletes only rows older than its own run. Rows an earlier version deleted are not repaired by the upgrade:
  `python manage.py fill-read-model --channel_idx <channel>` restores them.

## 4.4.0 — 2026-10-12

- Optional sibling apps that are installed but not enabled no longer crash imports (`RuntimeError` is caught like
  `ImportError`).

### Security

- The public v2 views (products, count, options, search, categories, stock, omnibus) declare
  `authentication_classes = []` and `AllowAny`. They declared none, so a service that leaves DRF's defaults (session
  and Basic) evaluated `Authorization: Basic` on them: the answer differed for a right and a wrong password, outside
  any login throttle. Credentials are now ignored there; `prices/` keeps JWT.

## 4.3.0 — 2026-08-06

- Ranged bundle pricing and product variant groups.
- `MATRIX_SEARCH_DEFAULT_SORT` setting; prefetch optimizations.
- `/products/` and `/products/count/` now read `?search=`. The param was accepted and silently dropped, so a search on v2 returned the full unfiltered catalogue with HTTP 200 while v1 filtered correctly. Matching fields are the ones the channel marks as searchable (always `sku`, plus `name` and any searchable feature).
- **Ordering change on channels with `MATRIX_FULL_TEXT_SEARCH` enabled:** `/products/?search=` with no explicit `s_` sort now orders by relevance (`search_rank DESC`) instead of the channel default. With full-text search off (the default) the order is unchanged — only the result set shrinks.
- `/search/` sorts by relevance descending. It used to ask for `relevance ASC`, which on a ranked search means worst matches first. The effect was masked on channels without full-text search, where the relevance sort is skipped entirely.
- `/search/` `products.total` is the number of matching products. It used to be the page size, so a storefront paginating on `total` always computed a single page.
- Unknown query params surface as a `param.unknown` warning in `meta.warnings` on `/products/`, `/products/count/` and `/search/`. They are still ignored and HTTP stays 200 — consumers that forward a whole browser query string (tracking params on a category URL) keep working. `limit` is not an alias for `page_size` on v2 and now reports itself as unknown.
- `/search/` responses below the 2-character minimum now carry the `meta` envelope like every other path.
- Full-text search no longer returns HTTP 500 on a language Postgres does not know. The text search configuration is resolved against what the server actually reports rather than taken from `Language.name_en`, falling back to `simple` — `?language=pl` used to produce `to_tsvector('polish', ...)`, which does not exist. Only affects channels with `MATRIX_FULL_TEXT_SEARCH` enabled.
- Search terms containing `<`, `>`, `*`, `"` or `\` no longer return HTTP 500. The tsquery sanitiser is an allowlist instead of a six-character denylist. Apostrophes are no longer doubled, so `O'Brien` is searched as typed. Terms now split on dots, so `3.5mm` is matched as `3` and `5mm`.

## 4.2.0 — 2026-07-30

- Drop the withdrawn pricetuner extra.
- Stewardship metadata: maintainers in `pyproject.toml`, CODEOWNERS.

## 4.1.0 — 2026-07-13

- Promote soft integrations to extras: `[checkout]` (>=9.0.0), `[omnibus]` (>=3.0.0), `[reviews]` (>=2.0.0).
- Drop phantom `marshmallow-dataclass[enum, union]` extras.

## 4.0.0 — 2026-07-11

- Initial public release: read-optimized product data layer with the v2 storefront API — `s_`-prefixed sorting, `meta` warnings envelope, batch category lookups, channel-scoped filtering.
