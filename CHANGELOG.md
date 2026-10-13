# Changelog

## 4.4.0 — 2026-10-12

- Optional sibling apps that are installed but not enabled no longer crash imports (`RuntimeError` is caught like
  `ImportError`).

### Fixed

- Products no longer go missing from the read model after a seed or a large import. Two fills that overlapped on one
  channel (a full channel fill and a per-product fill, or the fills of a configurable product and of its variant)
  could delete rows the other had just written: a product, its translations and attributes, and with a configurable
  parent its variants too. A fill now holds a PostgreSQL session advisory lock for its channel for all of its steps,
  so a second fill of that channel waits and then runs; fills of different channels do not wait for each other. The
  cleanup deletes only rows older than its own run. Rows an earlier version deleted are not repaired by the upgrade:
  `python manage.py fill-read-model --channel_idx <channel>` restores them.

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
