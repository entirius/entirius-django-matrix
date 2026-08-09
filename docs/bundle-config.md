---
title: Bundle Config API
description: Matrix API endpoint for retrieving bundle product structure, sub-items, selection flags, limits, and prices.
---

The `bundle-config/` endpoint returns the full structure of a bundle product: sub-items with selection flags, quantity limits, and per-component prices. Used by the storefront to render the bundle product selector before adding to cart.

## Endpoint

```
GET /api/matrix/v1/{channel_idx}/bundle-config/
```

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sku[]` | list[str] | yes | Bundle SKUs (repeat for multiple) |
| `currency` | str | no | Currency code (ISO 4217, e.g. `EUR`) |
| `country` | str | no | Country code (ISO 3166-1, e.g. `DE`) |
| `language` | str | no | Language code (ISO 639-1, e.g. `en`) |

### Example Request

```
GET /api/matrix/v1/default-europe/bundle-config/?sku[]=ENT-BND01&currency=EUR&country=DE
```

Multiple bundles in one request:

```
GET /api/matrix/v1/default-europe/bundle-config/?sku[]=ENT-BND01&sku[]=ENT-BND02&currency=EUR&country=DE
```

## Response

Array of bundle objects — one per requested SKU.

```json
{
  "data": [
    {
      "sku": "ENT-BND01",
      "max_limit": 5,
      "min_limit": 2,
      "sub_items": [
        {
          "sku": "ENT-S001",
          "quantity": 1,
          "is_required": true,
          "is_default": true,
          "can_change_quantity": false,
          "price": {
            "sku": "ENT-S001",
            "is_range": false,
            "has_special_price": false,
            "price": "149.99",
            "special_price": null,
            "tax_amount": "0.23",
            "tax_rule": "23%",
            "promo_badge": null,
            "special_from_date": null,
            "special_to_date": null,
            "price_tax_config_opposite": "121.94",
            "special_price_tax_config_opposite": null,
            "omnibus_price": null
          }
        },
        {
          "sku": "ENT-C001",
          "quantity": 1,
          "is_required": false,
          "is_default": false,
          "can_change_quantity": true,
          "price": { "..." : "..." }
        }
      ]
    }
  ]
}
```

## Bundle Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `sku` | str | Bundle product SKU |
| `max_limit` | int \| null | Maximum total quantity of all active sub-products. From PIM attribute `max_limit_bundle`. |
| `min_limit` | int \| null | Minimum total quantity of optional sub-products. From PIM attribute `min_limit_bundle`. |
| `sub_items` | list | All sub-products in the bundle |

## Sub-Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `sku` | str | Sub-product SKU |
| `quantity` | int | Default quantity from `BundleLink` |
| `is_required` | bool | Always included in bundle; counts toward min/max limits |
| `is_default` | bool | Included when frontend does not explicitly declare `sub_items` |
| `can_change_quantity` | bool | Frontend may change quantity; `false` means `quantity` is fixed |
| `price` | object \| null | Sub-product price (same fields as `prices-bundle/`); `null` if no price available |

## CSV Import

Bundle extension fields are set via the `bundle_sku` column in the products CSV. See [CSV Format — Bundle Product Columns](/volkanos/modules/pim/pim-csv/csv-format/#bundle-product-columns) for the format specification.

## PIM Configuration

Limits require two PIM features to be configured:

- `max_limit_bundle` — feature with type TEXT, assigned to the bundle feature set
- `min_limit_bundle` — feature with type TEXT, assigned to the bundle feature set

These are stored as text attributes on the bundle product and cast to integers by the API.
