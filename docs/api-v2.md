---
title: API v2
description: Matrix API v2 — storefront-optimized product data endpoints
---

Matrix v2 is the DRF storefront API: explicit gross/net pricing, include groups, pre-grouped filter
options, and unified search. It runs at `/api/matrix/v2/<channel_idx>/` alongside the untouched v1.

The full reference — every endpoint, parameter, filter, and response schema — lives in the
interactive **[Storefront API explorer](/api/storefront/#tag/matrix-products)**. It is generated from the code
(drf-spectacular) and regenerated on each release. Start with the `Matrix Products`,
`Matrix Options`, and `Matrix Search` tags.

:::tip[Filtering]
Filter with the `q_{feature_idx}` (value) and `r_{feature_idx}` (range) query params — `q_color=red`,
`r_price=100&r_price=500`. They are the backend filter contract, documented per endpoint in the explorer.
The `options/` endpoint returns the available filters with context-sensitive counts for the sidebar.
:::

:::tip[Sorting]
Sort with the `s_{field}={dir}` prefix — `s_price=desc`, `s_created=desc`. Same shape as the `q_` / `r_`
filters. Repeat for multi-sort (`s_price=desc&s_name=asc`) — URL order is precedence. System fields:
`price`, `name`, `created`, `sku`, `on_stock`, `relevance`; plus any sortable feature idx. The old
`sort` / `sort_dir` params were removed in 3.2.0.
:::

:::note[Ignored params don't fail silently]
`/products/`, `/products/count/`, and `/search/` return a `meta` envelope:
`{ "status": "ok" | "warning", "warnings": [{ "code", "param", "message" }] }`. If you send a `q_`/`r_`/`s_`
param the backend can't apply (typo, non-sortable field), the request still succeeds (200) but `meta.warnings`
names the offending `param` and a stable `code`. Empty `warnings` = everything applied.
:::

For release history see the [Changelog](/volkanos/modules/matrix/changelog/). Internal response shapes and
architectural decisions live in `django-matrix/docs/api-v2-*.md`.
