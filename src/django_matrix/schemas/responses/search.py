# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Response schemas of v2 `search/` — documentation only, the view returns the service's dict."""

from pydantic import BaseModel, ConfigDict, Field

from django_matrix.schemas.responses.common import ResponseMeta
from django_matrix.schemas.responses.product import ProductCore


class SearchProducts(BaseModel):
    """Products section: the items are the results of `products/` (`include` works the same)."""

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(description="Number of matches (not the page size)", examples=[42])
    results: list[ProductCore] = Field(description="Products in the shape of `products/` results")
    has_next_page: bool = Field(description="True if more results exist after this page", examples=[False])


class SearchCategoryItem(BaseModel):
    idx: str = Field(description="Category idx", examples=["sofas"])
    name: str = Field(description="Translated category name", examples=["Sofas"])
    url_key: str = Field(description="URL slug (current language)", examples=["sofas"])
    image_url: str | None = Field(None, description="Category image URL")
    products_count: int = Field(description="Reserved, currently 0", examples=[0])


class SearchCategories(BaseModel):
    results: list[SearchCategoryItem] = Field(description="Categories whose name matches the query")


class SearchPhrase(BaseModel):
    text: str = Field(description="Suggested phrase", examples=["corner sofa"])
    type: str = Field(description="Kind of suggestion", examples=["completion"])


class SearchResponse(BaseModel):
    """Sections follow `scope`: `products` and `categories` appear only when asked for."""

    model_config = ConfigDict(from_attributes=True)

    products: SearchProducts | None = Field(None, description="Present when `scope` has `products`")
    categories: SearchCategories | None = Field(None, description="Present when `scope` has `categories`")
    phrases: list[SearchPhrase] = Field(description="Phrase completions from product names")
    meta: ResponseMeta = Field(description="Status + warnings for ignored filter/sort params")
