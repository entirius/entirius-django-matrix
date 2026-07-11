# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Product response schemas for v2 API. Per Decision #34: every price field MUST document relationships."""

from pydantic import BaseModel, ConfigDict, Field


class SourceSetItem(BaseModel):
    source: str = Field(description="Image URL path", examples=["/media/thumb/59/f0/example.webp"])
    width: int = Field(description="Image width in pixels", examples=[320])
    height: int = Field(description="Image height in pixels", examples=[320])


class MainImageResponse(BaseModel):
    source_set: list[SourceSetItem] = Field(description="Responsive image sources sorted by width")
    alt_text: str | None = Field(None, description="Alt text for accessibility", examples=["Ergonomic Chair"])


class BadgeBrandItem(BaseModel):
    """System SELECT attribute from PIM (badge, subname, brand)."""

    idx: str = Field(description="Machine identifier for filtering/analytics/CSS hooks", examples=["bestseller"])
    name: str = Field(description="Translated display label", examples=["Chapter Approved"])
    extension: dict | None = Field(None, description="Optional visual asset (icon URL, color hash)")


class FeatureSetResponse(BaseModel):
    idx: str = Field(description="Feature set identifier", examples=["furniture"])
    name: str = Field(description="Feature set display name", examples=["Furniture"])


class CategoryResponse(BaseModel):
    idx: str = Field(description="PIM ProductCategory.idx", examples=["office-chairs"])
    name: str = Field(description="Translated category name", examples=["Office Chairs"])
    url_key: str = Field(description="Translated URL key", examples=["office-chairs"])
    path: list[dict] | None = Field(
        None,
        description="Breadcrumb path from root. Present only with include=full. Each item: {name, url_key}",
        examples=[
            [{"name": "Furniture", "url_key": "furniture"}, {"name": "Office Chairs", "url_key": "office-chairs"}]
        ],
    )


class PriceResponse(BaseModel):
    """Price object — always includes both gross and net.

    Price logic:
    - gross/net: catalog price (regular, before promotions). Used for strikethrough display.
    - final_gross/final_net: price customer pays. Equals special when promo active, otherwise equals gross.
    - special_gross/special_net: promotional price. Null when no promotion.
    - When is_range=true (configurable/bundle): scalar fields are null, use range_from/to.
    - These states are mutually exclusive — never both scalar and range populated.
    """

    currency: str = Field(description="ISO 4217 currency code", examples=["EUR"])
    tax_rate: str = Field(description="Tax rate as decimal string", examples=["0.23"])
    is_range: bool = Field(description="True for CONFIGURABLE/BUNDLE parents with price range", examples=[False])

    gross: str | None = Field(None, description="Catalog price gross. Null when is_range=true", examples=["349.00"])
    net: str | None = Field(None, description="Catalog price net. Null when is_range=true", examples=["283.74"])
    final_gross: str | None = Field(
        None,
        description="Price customer pays (gross). = special_gross if promo active, else = gross. Null when is_range=true",
        examples=["299.00"],
    )
    final_net: str | None = Field(
        None,
        description="Price customer pays (net). = special_net if promo active, else = net. Null when is_range=true",
        examples=["243.09"],
    )

    has_special_price: bool = Field(description="True when promotion is active", examples=[True])
    special_gross: str | None = Field(
        None, description="Promotional price gross. Null when no promo", examples=["299.00"]
    )
    special_net: str | None = Field(None, description="Promotional price net. Null when no promo", examples=["243.09"])
    percent_off: int | None = Field(
        None,
        description="Discount percentage (int). Worker-computed: round(100 - special/gross * 100). Null when no promo",
        examples=[14],
    )
    special_from_date: str | None = Field(
        None, description="Promo start date (ISO 8601). Null when no promo or open-ended"
    )
    special_to_date: str | None = Field(None, description="Promo end date (ISO 8601). Null when no promo or open-ended")

    range_from_gross: str | None = Field(
        None, description="Min variant price gross. Null when is_range=false", examples=["249.00"]
    )
    range_from_net: str | None = Field(
        None, description="Min variant price net. Null when is_range=false", examples=["202.44"]
    )
    range_to_gross: str | None = Field(
        None, description="Max variant price gross. Null when is_range=false", examples=["399.00"]
    )
    range_to_net: str | None = Field(
        None, description="Max variant price net. Null when is_range=false", examples=["324.39"]
    )
    range_from_special_gross: str | None = Field(None, description="Min variant promo gross")
    range_from_special_net: str | None = Field(None, description="Min variant promo net")
    range_to_special_gross: str | None = Field(None, description="Max variant promo gross")
    range_to_special_net: str | None = Field(None, description="Max variant promo net")


class AttributeResponse(BaseModel):
    """Product attribute with PIM flags for frontend filtering."""

    feature_idx: str = Field(description="PIM Feature.idx", examples=["color"])
    feature_name: str = Field(description="Translated feature name", examples=["Color"])
    feature_type: str = Field(description="PIM FeatureType enum value", examples=["SELECT"])
    value: str | None = Field(
        None, description="Translated display value. BOOL: 'Yes'/'Tak'. SELECT: translated name", examples=["Red"]
    )
    value_idx: str | None = Field(
        None,
        description="Machine identifier for filtering. BOOL: 'true'/'false'. SELECT: PIM Attribute.idx. Null for text/decimal",
        examples=["red"],
    )
    is_visible: bool = Field(description="PIM flag: show in product attribute list")
    has_visual_asset: bool = Field(description="PIM flag: has swatch/icon in extension")
    is_comparable: bool = Field(description="PIM flag: show on comparison page")
    extension: dict | None = Field(None, description="Visual asset data (image URL, color hash)")
    group_idx: str | None = Field(
        None, description="AttributesGroup.idx — group key for frontend sections", examples=["dimensions"]
    )
    group_name: str | None = Field(None, description="Translated group display name", examples=["Dimensions"])
    group_position: int | None = Field(None, description="Sort order within group", examples=[10])


class MediaItem(BaseModel):
    """Unified gallery item — image or video, sorted by position."""

    type: str = Field(description="Media type: 'image' or 'video'", examples=["image"])
    position: int = Field(description="Sort order in gallery", examples=[0])
    role: str | None = Field(None, description="Media role: main, general, variant, angle", examples=["main"])
    source_set: list[dict] = Field(
        default_factory=list,
        description="Sources: images have {source, width, height}, videos have {title, url, source}",
    )
    alt_text: str | None = Field(None, description="Alt text for accessibility (images only)", examples=["Front view"])
    video_source: str | None = Field(
        None, description="Video provider: youtube, vimeo, unknown (videos only)", examples=["youtube"]
    )


class AttachmentResponse(BaseModel):
    """Product file attachment (PDF, document, etc.) from PIM."""

    file_label: str | None = Field(None, description="Translated label for display", examples=["Installation Manual"])
    original_file_name: str | None = Field(None, description="Original uploaded filename", examples=["manual-v2.pdf"])
    file_path: str | None = Field(
        None, description="Download URL path (relative)", examples=["/media/files/abc123.pdf"]
    )
    file_type: str = Field(description="File type: pdf, doc, picture, video, undefined", examples=["pdf"])
    file_size: str | None = Field(None, description="File size/weight", examples=["2.45"])
    category_code: str | None = Field(None, description="FilesCategory.code", examples=["manuals"])
    category_name: str | None = Field(
        None, description="Translated category name (resolved for current language)", examples=["Manuals"]
    )


class ProductCore(BaseModel):
    """Core product fields — always present in listing and detail."""

    model_config = ConfigDict(from_attributes=True)

    sku: str = Field(description="Product SKU", examples=["ENT-CFG01"])
    product_type: str = Field(description="SIMPLE | CONFIGURABLE | BUNDLE | CUSTOM", examples=["CONFIGURABLE"])
    is_virtual: bool = Field(description="False=physical, True=virtual", examples=[False])
    url_key: str = Field(description="URL slug (current language)", examples=["ergonomic-chair"])

    name: str = Field(description="Product name (translated)", examples=["Ergonomic Office Chair"])
    main_image: MainImageResponse | None = Field(None, description="Pre-resolved main image with source_set")
    badges: list[BadgeBrandItem] | None = Field(None, description="System SELECT attributes from PIM (badge)")
    subnames: list[BadgeBrandItem] | None = Field(None, description="Additional name labels")
    brands: list[BadgeBrandItem] | None = Field(None, description="Brand SELECT attributes from PIM")

    feature_set: FeatureSetResponse | None = Field(None, description="Product's feature set")
    on_stock: bool | None = Field(None, description="Stock status. Null when QMS unavailable (not false)")
    parent_sku: str | None = Field(None, description="Parent product SKU (for variants on listing)")
    parent_url_key: str | None = Field(None, description="Parent URL key")

    review_rating: str | None = Field(
        None, description="Average rating (decimal). Null when reviews module absent", examples=["4.50"]
    )
    review_count: int | None = Field(
        None, description="Number of reviews. Null when reviews module absent", examples=[23]
    )

    price: PriceResponse | None = Field(None, description="Public price. Null when no public price exists")

    categories: list[CategoryResponse] = Field(
        default_factory=list,
        description="Categories this product belongs to (for GA4). With include=full: extended with path (breadcrumbs)",
    )
