# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class FilterOption(DTO):
    position: int = 0
    label: str | None = None
    idx: str | None = None
    products_count: int = 0
    extension: str | None = None

    @staticmethod
    def factory(option: dict | None = None):
        if option is None:
            option = {}
        return FilterOption(
            position=option["position"] if "position" in option else 0,
            label=option["label"] if "label" in option else None,
            idx=option["idx"] if "idx" in option else None,
            products_count=option["products_count"] if "products_count" in option else 0,
            extension=option["extension"] if "extension" in option else None,
        )
