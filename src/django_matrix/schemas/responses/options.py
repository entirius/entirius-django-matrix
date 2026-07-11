# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Options response schema — pre-grouped sort/ranges/filters."""

from pydantic import BaseModel, Field


class SortOption(BaseModel):
    idx: str = Field(
        description="Sort field. System: price, name, created, sku, on_stock, relevance. Or feature_idx",
        examples=["price"],
    )
    label: str = Field(description="Translated display label", examples=["Price"])
    position: int = Field(description="Sort order", examples=[0])


class RangeFilter(BaseModel):
    idx: str = Field(description="Feature idx (e.g. 'price', 'weight')", examples=["price"])
    label: str = Field(description="Translated display label", examples=["Price"])
    position: int = Field(description="Display order", examples=[0])
    min: float | None = Field(None, description="Minimum value in current filter context", examples=[10.0])
    max: float | None = Field(None, description="Maximum value in current filter context", examples=[999.0])


class FilterValue(BaseModel):
    idx: str | bool = Field(description="Attribute idx (string for SELECT, bool for BOOLEAN)", examples=["red"])
    label: str = Field(description="Translated display label", examples=["Red"])
    count: int = Field(description="Product count with this value in current context", examples=[15])
    position: int = Field(description="Display order", examples=[1])
    extension: dict | None = Field(None, description="Visual asset (swatch image, color hash)")


class FilterGroup(BaseModel):
    idx: str = Field(description="Feature idx", examples=["color"])
    label: str = Field(description="Translated feature name", examples=["Color"])
    widget_type: str = Field(
        description="UI hint: default | swatch_image | swatch_text | boolean", examples=["swatch_image"]
    )
    position: int = Field(description="Display order", examples=[10])
    is_or_filter: bool = Field(
        description="True: OR logic (any selected). False: AND logic (all selected)", examples=[True]
    )
    values: list[FilterValue] = Field(description="Available filter values with counts")


class OptionsResponse(BaseModel):
    """Pre-grouped options — frontend renders directly, no normalization needed."""

    sort: list[SortOption] = Field(description="Available sort fields")
    ranges: list[RangeFilter] = Field(description="Range filters (price, decimal features)")
    filters: list[FilterGroup] = Field(description="Select/multiselect/boolean filters with counts")
