# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class OptionValue(DTO):
    value: str
    label: str
    position: int
    extension: list | None = None


@dataclass
class Option(DTO):
    idx: str
    label: str
    widget_type: str
    widget_behaviour: str
    position: int
    options: list[OptionValue]
    extra_value: dict | None = None


@dataclass
class VariantAttribute(DTO):
    feature_idx: str
    feature_label: str
    value_idx: str
    value_label: str
    extension: list | None = None


@dataclass
class AdditionalData(DTO):
    feature_idx: str
    feature_label: str
    value: str


@dataclass
class Variant(DTO):
    sku: str
    on_stock: bool
    additional_data: list[AdditionalData]
    attributes: list[VariantAttribute]
