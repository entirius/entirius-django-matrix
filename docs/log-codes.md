# Log Codes

| Process                                               | Level | Code | Description                                                            |
|-------------------------------------------------------|-------|------|------------------------------------------------------------------------|
| Fill read model - products and attributes             | Error | 4001 | Error while matching simple to config and saving ProductRepresentation |
| Fill read model - products and attributes             | Error | 4002 | Error while creating ProductRepresentation                             |
| Fill read model - products and attributes             | Error | 4003 | Error while updating existing ProductRepresentation                    |
| Fill read model - products and attributes             | Error | 4004 | Error while creating ProductT9N                                        |
| Fill read model - products and attributes             | Error | 4005 | Error while updating existing ProductT9N                               |
| Fill read model - products and attributes             | Error | 4006 | Error while creating Attribute                                         |
| Fill read model - products and attributes             | Error | 4007 | Error while gathering readmodel data                                   |
| Fill read model - fill read model prices              | Error | 4008 | Error while creating ProductPrice                                      |
| Fill read model - fill read model prices              | Error | 4009 | Error while updating existing ProductRepresentation                    |
| Fill read model - fill read model prices              | Error | 4010 | Error while creating ProductPrice for product parent                   |
| Fill read model - fill read model prices              | Error | 4011 | Error while updating existing ProductRepresentation for product parent |
| Fill read model - fill read model prices              | Error | 4012 | Error when trying to ProductPrice data                                 |
| Fill read model - fill read model pictures and thumbs | Error | 4013 | Error while saving picture for product                                 |
| Fill read model - fill read model pictures and thumbs | Error | 4014 | General error for creating/updating pictures in ProductRepresentation  |
| Fill read model - fill read model pictures and thumbs | Error | 4015 | Error while removing product pictures to keep them up to date.         |
| Fill read model - fill read model on stock            | Error | 4016 | Error while updating on_stock for existing ProductRepresentation       |
| Fill read model - products and attributes             | Error | 4017 | Error while gathering attributes                                       |
| Fill read model - fill read model on stock            | Error | 4018 | Error while gathering quantities                                       |
| Fill read model - fill read model pictures and thumbs | Error | 4019 | Error while gathering ProductT9N for sku and language to save picture  |
| Fill read model - fill read model videos              | Error | 4020 | Error while saving videos for product                                  |
| Fill read model - fill read model videos              | Error | 4021 | General error for creating/updating videos in ProductRepresentation    |
| Fill read model - fill read model videos              | Error | 4022 | Error while removing product videos to keep them up to date.           |
| Fill read model - fill read model videos              | Error | 4023 | Error while gathering ProductT9N for sku and language to save videos   |
| Fill read model - fill read model prices              | Error | 4024 | General error for while creating/calculating product ProductPrice      |
| Fill read model - fill read model prices              | Error | 4025 | Min/max offer price cannot be imported bcs of Import ERROR/Exception   |
| Fill read model - products and attributes             | Error | 4026 | Language doesn't exists in django_regional                             |
| Fill read model - fill read model on stock            | Error | 4027 | There is no subproduct Stock in checkout table                         |
| Fill read model - fill read model on stock            | Error | 4028 | Error fetching quantities from source Checkout/QMS                     |
| Fill read model - products representations            | Error | 4029 | Bulk create updated failed                                             |
| Fill read model - products t9n                        | Error | 4030 | Bulk create updated failed                                             |
| Fill read model - attributes                          | Error | 4031 | Bulk create updated failed                                             |
| Fill read model - products representations            | Error | 4032 | Too many products representations to delete. Operation stopped.        |
| Fill read model - products t9n                        | Error | 4033 | Too many products t9n to delete. Operation stopped.                    |
| Fill read model - attributes                          | Error | 4034 | Too many attributes to delete. Operation stopped.                      |

| Process                                   | Level   | Code | Description                                              |
|-------------------------------------------|---------|------|----------------------------------------------------------|
| Fill read model - products and attributes | Warning | 3001 | Can't find ProductRepresentation to assign to ProductT9n |
| Fill read model - products and attributes | Warning | 3002 | Can't find ProductRepresentation to assign to Attribute  |


| Process                                               | Level | Code | Description                                                                                                         |
|-------------------------------------------------------|-------|------|---------------------------------------------------------------------------------------------------------------------|
| Fill read model - products and attributes             | Info  | 2001 | Product has been skipped because it is disabled.                                                                    |
| Fill read model - products and attributes             | Info  | 2002 | ProductRepresentation has been created/updated.                                                                     |
| Fill read model - products and attributes             | Info  | 2003 | All previous ProductRepresentation have been deleted.                                                               |
| Fill read model - products and attributes             | Info  | 2004 | ProductT9N has been created/updated.                                                                                |
| Fill read model - products and attributes             | Info  | 2005 | All previous ProductT9n correlated have been deleted.                                                               |
| Fill read model - products and attributes             | Info  | 2006 | All previous attribute correlated with product sku have been deleted. Next the up-to-date attributes will be added. |
| Fill read model - products and attributes             | Info  | 2007 | Attribute skipped. This attribute has likely been saved in ProductT9N                                               |
| Fill read model - products and attributes             | Info  | 2008 | Attribute created/updated for product.                                                                              |
| Fill read model - products and attributes             | Info  | 2018 | Attribute skipped. This product attribute has empty value.                                                          |
| Fill read model - products and attributes             | Info  | 2027 | Attribute skipped. Product feature set not matching feature features sets                                           |
| Fill read model - fill read model prices              | Info  | 2009 | ProductPrice saved/updated for product.                                                                             |
| Fill read model - fill read model prices              | Info  | 2010 | ProductPrice created for product.                                                                                   |
| Fill read model - fill read model prices              | Info  | 2011 | ProductPrice saved/updated for product parent.                                                                      |
| Fill read model - fill read model prices              | Info  | 2012 | ProductPrice created for product parent.                                                                            |
| Fill read model - fill read model prices              | Info  | 2013 | Price skipped. There is no sku product in ProductRepresentation.                                                    |
| Fill read model - fill read model on stock            | Info  | 2014 | On_stock updated.                                                                                                   |
| Fill read model - fill read model on stock            | Info  | 2015 | Stock skipped. There is no sku product in ProductRepresentation.                                                    |
| Fill read model - fill read model pictures and thumbs | Info  | 2016 | ProductRepresentation sku pictures saved/updated.                                                                   |
| Fill read model - fill read model pictures and thumbs | Info  | 2017 | Remove product pictures to keep them up to date.                                                                    |
| Fill read model - fill read model pictures and thumbs | Info  | 2018 | ProductRepresentation sku pictures t9n saved/updated.                                                               |
| Fill read model - fill read model pictures and thumbs | Info  | 2019 | Remove product pictures t9n to keep them up to date.                                                                |
| Fill read model - fill read model videos              | Info  | 2020 | ProductRepresentation sku videos saved/updated.                                                                     |
| Fill read model - fill read model videos              | Info  | 2021 | Remove product videos to keep them up to date.                                                                      |
| Fill read model - fill read model videos              | Info  | 2022 | ProductRepresentation sku videos t9n saved/updated.                                                                 |
| Fill read model - fill read model videos              | Info  | 2023 | Remove product videos t9n to keep them up to date.                                                                  |
| Fill read model - products and attributes             | Info  | 2024 | ProductRepresentation has been added to save queue.                                                                 |
| Fill read model - products and attributes             | Info  | 2025 | ProductT9N has been added to save queue.                                                                            |
| Fill read model - products and attributes             | Info  | 2026 | Attribute has been added to save queue.                                                                             |


| Process | Level | Code | Description |
|---------|-------|------|-------------|
|         | Debug | 1001 |             |

# API Log Codes
| Process                                               | Level | Code | Description                                                            |
|-------------------------------------------------------|-------|------|------------------------------------------------------------------------|
| API - product_urls_view                               | Error | 4501 | Language doesn't exists in django_regional                             |

