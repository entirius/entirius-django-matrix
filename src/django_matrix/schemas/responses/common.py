# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Common response schemas shared across v2 endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class WarningItem(BaseModel):
    """Non-blocking feedback for a single q_/r_/s_ param the backend could not apply."""

    code: str = Field(description="Stable machine-readable code", examples=["sort.not_sortable"])
    param: str = Field(description="The query param that was ignored", examples=["s_db_created"])
    message: str = Field(
        description="Human-readable detail", examples=["feature_idx db_created is not sortable in channel"]
    )


class ResponseMeta(BaseModel):
    """Always present. `status` is `warning` when any param was ignored, else `ok`."""

    status: str = Field(description="`ok` | `warning`", examples=["ok"])
    warnings: list[WarningItem] = Field(
        default_factory=list, description="Ignored q_/r_/s_ params (empty = all applied)"
    )


class PaginatedResponse(BaseModel):
    """Lightweight pagination envelope. No COUNT — uses has_next_page (LIMIT+1 trick)."""

    model_config = ConfigDict(from_attributes=True)

    has_next_page: bool = Field(description="True if more results exist after this page", examples=[True])
    page: int = Field(description="Current page number (1-based)", examples=[1])
    page_size: int = Field(description="Results per page", examples=[12])
    results: list = Field(description="Page results", examples=[[]])
    meta: ResponseMeta = Field(description="Status + warnings for ignored filter/sort params")


class CountResponse(BaseModel):
    """Response for products/count/ endpoint."""

    model_config = ConfigDict(from_attributes=True)

    count: int = Field(description="Total number of products matching filters", examples=[142])
    meta: ResponseMeta = Field(description="Status + warnings for ignored filter params")
