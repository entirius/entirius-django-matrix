---
title: Log Codes
description: Error, warning, info, debug, and API log codes emitted by django-matrix during read model builds and API requests.
---

Log codes are emitted via `ProcessLogger` during read model fill workers and via the standard logger during API requests.

## Errors (4xxx)

| Code | Process | Description |
|------|---------|-------------|
| 4001 | Fill — products and attributes | Error matching a simple product to its configurable parent and saving ProductRepresentation |
| 4002 | Fill — products and attributes | Error creating ProductRepresentation |
| 4003 | Fill — products and attributes | Error updating an existing ProductRepresentation |
| 4004 | Fill — products and attributes | Error creating ProductT9N |
| 4005 | Fill — products and attributes | Error updating an existing ProductT9N |
| 4006 | Fill — products and attributes | Error creating Attribute |
| 4007 | Fill — products and attributes | Error gathering read model data |
| 4008 | Fill — prices | Error creating ProductPrice |
| 4009 | Fill — prices | Error updating an existing ProductRepresentation (price step) |
| 4010 | Fill — prices | Error creating ProductPrice for a product parent |
| 4011 | Fill — prices | Error updating an existing ProductRepresentation for a product parent |
| 4012 | Fill — prices | Error retrieving ProductPrice data |
| 4013 | Fill — pictures | Error saving a picture for a product |
| 4014 | Fill — pictures | General error creating or updating pictures in ProductRepresentation |
| 4015 | Fill — pictures | Error removing outdated product pictures |
| 4016 | Fill — stock | Error updating `on_stock` for an existing ProductRepresentation |
| 4017 | Fill — products and attributes | Error gathering attributes |
| 4018 | Fill — stock | Error gathering quantities from source (Checkout/QMS) |
| 4019 | Fill — pictures | Error retrieving ProductT9N for SKU and language when saving a picture |
| 4020 | Fill — videos | Error saving videos for a product |
| 4021 | Fill — videos | General error creating or updating videos in ProductRepresentation |
| 4022 | Fill — videos | Error removing outdated product videos |
| 4023 | Fill — videos | Error retrieving ProductT9N for SKU and language when saving videos |
| 4024 | Fill — prices | General error creating or calculating ProductPrice |
| 4025 | Fill — prices | Min/max offer price cannot be imported due to an error or exception |
| 4026 | Fill — products and attributes | Language does not exist in django-regional |
| 4027 | Fill — stock | No sub-product stock record found in checkout table |
| 4028 | Fill — stock | Error fetching quantities from Checkout or QMS |
| 4029 | Fill — product representations | Bulk create/update failed |
| 4030 | Fill — product t9n | Bulk create/update failed |
| 4031 | Fill — attributes | Bulk create/update failed |
| 4032 | Fill — product representations | Too many ProductRepresentation rows would be deleted. Operation stopped. See `DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR`. |
| 4033 | Fill — product t9n | Too many ProductT9N rows would be deleted. Operation stopped. |
| 4034 | Fill — attributes | Too many Attribute rows would be deleted. Operation stopped. |

## Warnings (3xxx)

| Code | Process | Description |
|------|---------|-------------|
| 3001 | Fill — products and attributes | Cannot find a ProductRepresentation to assign to a ProductT9N |
| 3002 | Fill — products and attributes | Cannot find a ProductRepresentation to assign to an Attribute |

## Info (2xxx)

| Code | Process | Description |
|------|---------|-------------|
| 2001 | Fill — products and attributes | Product skipped — disabled in PIM |
| 2002 | Fill — products and attributes | ProductRepresentation created or updated |
| 2003 | Fill — products and attributes | All previous ProductRepresentation rows deleted |
| 2004 | Fill — products and attributes | ProductT9N created or updated |
| 2005 | Fill — products and attributes | All previous ProductT9N rows for this product deleted |
| 2006 | Fill — products and attributes | All previous Attribute rows for this SKU deleted before re-adding |
| 2007 | Fill — products and attributes | Attribute skipped — already saved in ProductT9N |
| 2008 | Fill — products and attributes | Attribute created or updated for product |
| 2009 | Fill — prices | ProductPrice saved or updated |
| 2010 | Fill — prices | ProductPrice created |
| 2011 | Fill — prices | ProductPrice saved or updated for parent product |
| 2012 | Fill — prices | ProductPrice created for parent product |
| 2013 | Fill — prices | Price skipped — no ProductRepresentation for this SKU |
| 2014 | Fill — stock | `on_stock` updated |
| 2015 | Fill — stock | Stock skipped — no ProductRepresentation for this SKU |
| 2016 | Fill — pictures | ProductRepresentation pictures saved or updated |
| 2017 | Fill — pictures | Outdated product pictures removed |
| 2018 | Fill — pictures | ProductT9N pictures saved or updated (also used for attribute-skipped info) |
| 2019 | Fill — pictures | Outdated ProductT9N pictures removed |
| 2020 | Fill — videos | ProductRepresentation videos saved or updated |
| 2021 | Fill — videos | Outdated product videos removed |
| 2022 | Fill — videos | ProductT9N videos saved or updated |
| 2023 | Fill — videos | Outdated ProductT9N videos removed |
| 2024 | Fill — products and attributes | ProductRepresentation added to save queue |
| 2025 | Fill — products and attributes | ProductT9N added to save queue |
| 2026 | Fill — products and attributes | Attribute added to save queue |
| 2027 | Fill — products and attributes | Attribute skipped — product feature set does not match required feature sets |

## Debug (1xxx)

| Code | Process | Description |
|------|---------|-------------|
| 1001 | — | Debug placeholder (no description) |

## API Codes (45xx)

| Code | Process | Description |
|------|---------|-------------|
| 4501 | API — `product_urls_view` | Language does not exist in django-regional |
