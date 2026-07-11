# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stock, Prices, Omnibus response schemas — batch SKU endpoints."""

from pydantic import BaseModel, Field


class StockItem(BaseModel):
    quantity: int = Field(description="Available quantity", examples=[5])
    is_in_stock: bool = Field(description="True if quantity > 0", examples=[True])


class OmnibusItem(BaseModel):
    currency: str = Field(description="ISO 4217", examples=["EUR"])
    omnibus_gross: str | None = Field(None, description="Lowest price gross in last 30 days", examples=["299.00"])
    omnibus_net: str | None = Field(None, description="Lowest price net in last 30 days", examples=["243.09"])
    status: str = Field(description="Price source: normal_price | special_price | discount", examples=["normal_price"])
