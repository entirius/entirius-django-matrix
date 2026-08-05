# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class ProductVariantDTO(DTO):
    sku: str
    label: str
    selected: bool
    on_stock: bool


@dataclass
class ProductVariantGroupDTO(DTO):
    attribute_label: str
    attribute_idx: str
    variants: list[ProductVariantDTO]
