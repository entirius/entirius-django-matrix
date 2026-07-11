# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class FilterableFeature(DTO):
    feature_idx: str | None = None
    feature_name: str | None = None
    filter_type: int | None = None
    position: int = 0
    is_or_filter: bool = False
    attribute_idx: str | None = None
    attribute_name: str | None = None
    display_order: int = 0
    extension: str | None = None
    product_count: int = 0

    @staticmethod
    def factory(data: dict | None = None):
        if data is None:
            data = {}

        return FilterableFeature(
            feature_idx=data.get("feature_idx"),
            feature_name=data.get("feature_name"),
            filter_type=data.get("filter_type"),
            position=data.get("position", 0),
            is_or_filter=data.get("is_or_filter", False),
            attribute_idx=data.get("attribute_idx"),
            attribute_name=data.get("attribute_name"),
            display_order=data.get("display_order", 0),
            extension=data.get("extension"),
            product_count=data.get("product_count", 0),
        )
