---
title: "Matrix: Database Diagrams"
description: "Auto-generated ER diagrams for the Matrix module."
sidebar:
  badge:
    text: "Auto-gen"
    variant: "note"
---

:::caution[Auto-generated]
These diagrams are auto-generated from Django model introspection.
Do not edit. Run `make erd` in entirius-docker to regenerate.
:::

## Channel & Feature Configuration

```d2 layout=elk
Channel: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  default_language_id: int {constraint: foreign_key}
  default_currency_id: int {constraint: foreign_key}
  default_country_id: int {constraint: foreign_key}
  idx: varchar
  "label": varchar
  default_order: varchar
  default_order_direction: varchar
}

FilterableFeatures: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  channel_id: int {constraint: foreign_key}
  feature_id: int {constraint: foreign_key}
  is_or_filter: bool
  position: int
}

SortableFeatures: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  channel_id: int {constraint: foreign_key}
  feature_id: int {constraint: foreign_key}
  position: int
}

SearchableFeatures: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  channel_id: int {constraint: foreign_key}
  feature_id: int {constraint: foreign_key}
}

VisibilityFeatures: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  channel_id: int {constraint: foreign_key}
  feature_id: int {constraint: foreign_key}
  position: int
}

Country: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Country (External: django_regional)"
}

Currency: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Currency (External: django_regional)"
}

Feature: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Feature (External: django_pim)"
}

Language: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Language (External: django_regional)"
}



Channel.default_language_id -> Language.id: {style.stroke: "#484B57"}

Channel.default_currency_id -> Currency.id: {style.stroke: "#484B57"}

Channel.default_country_id -> Country.id: {style.stroke: "#484B57"}

Channel.id <-> Language.id: {style.stroke: "#484B57"}

Channel.id <-> Currency.id: {style.stroke: "#484B57"}

Channel.id <-> Country.id: {style.stroke: "#484B57"}

FilterableFeatures.channel_id -> Channel.id: {style.stroke: "#00ACC1"}

FilterableFeatures.feature_id -> Feature.id: {style.stroke: "#484B57"}

SortableFeatures.channel_id -> Channel.id: {style.stroke: "#00ACC1"}

SortableFeatures.feature_id -> Feature.id: {style.stroke: "#484B57"}

SearchableFeatures.channel_id -> Channel.id: {style.stroke: "#00ACC1"}

SearchableFeatures.feature_id -> Feature.id: {style.stroke: "#484B57"}

VisibilityFeatures.channel_id -> Channel.id: {style.stroke: "#00ACC1"}

VisibilityFeatures.feature_id -> Feature.id: {style.stroke: "#484B57"}
```

## Product Read Model

```d2 layout=elk
ProductRepresentation: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  channel_id: int {constraint: foreign_key}
  parent_id: int {constraint: foreign_key}
  sku: varchar
  product_type: varchar
  kind_of_product: varchar
  on_stock: bool
  url_keys: jsonb
}

ProductPrice: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  product_representation_id: int {constraint: foreign_key}
  currency_id: int {constraint: foreign_key}
  country_id: int {constraint: foreign_key}
  is_range: bool
  has_special_price: bool
  price: decimal
  final_price: decimal
}

ProductT9N: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  product_representation_id: int {constraint: foreign_key}
  language_id: int {constraint: foreign_key}
  name: varchar
  desc: text
  short_desc: text
  url_key: varchar
  badges: jsonb
}

Attribute: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  product_id: int {constraint: foreign_key}
  hash: varchar
  feature_idx: varchar
  feature_name_t9n: jsonb
  feature_type: varchar
  feature_is_for_customization: bool
  attribute_idx: varchar
}

Channel: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Channel (See channel-features diagram)"
}

Country: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Country (External: django_regional)"
}

Currency: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Currency (External: django_regional)"
}

Language: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Language (External: django_regional)"
}



ProductRepresentation.channel_id -> Channel.id: {style.stroke: "#484B57"}

ProductRepresentation.parent_id -> ProductRepresentation.id: {style.stroke: "#00ACC1"}

ProductPrice.product_representation_id -> ProductRepresentation.id: {style.stroke: "#00ACC1"}

ProductPrice.currency_id -> Currency.id: {style.stroke: "#484B57"}

ProductPrice.country_id -> Country.id: {style.stroke: "#484B57"}

ProductT9N.product_representation_id -> ProductRepresentation.id: {style.stroke: "#00ACC1"}

ProductT9N.language_id -> Language.id: {style.stroke: "#484B57"}

Attribute.product_id -> ProductRepresentation.id: {style.stroke: "#00ACC1"}
```
