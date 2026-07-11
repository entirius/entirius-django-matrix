# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
from decimal import Decimal

from django_matrix.dto import DTO
from django_matrix.enums import FeatureType
from django_matrix.utils import bool_translate, convert_from_json


@dataclass
class AttributeDetailDTO(DTO):
    idx: str
    name: str
    picture: str | None = None
    color_hash: str | None = None
    is_default: bool | None = False
    group: str | None = None


@dataclass
class FeatureDTO(DTO):
    idx: str
    name: str
    attributes: list[AttributeDetailDTO]
    position: int
    feature_type: str
    frontend_input_type: str
    is_required: bool | None = False


@dataclass
class CustomFeature(FeatureDTO):
    excluded_color_hash: list | None = None


@dataclass
class Attribute(DTO):
    sku: str
    feature_idx: str
    feature_name: str
    feature_type: str
    attribute_value: str
    attribute_idx: str | None = None
    extension: dict | None = None

    # You can build Attribute view dto from db raw sql result
    def __init__(self, attribute: dict | None = None, language_iso2: str = "pl", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if attribute:
            self.sku = attribute["sku"] if "sku" in attribute else ""
            self.feature_idx = attribute["feature_idx"] if "feature_idx" in attribute else ""
            self.feature_name = attribute["feature_name"] if "feature_name" in attribute else ""
            self.feature_type = attribute["feature_type"] if "feature_type" in attribute else ""
            self.attribute_idx = attribute["attribute_idx"] if "attribute_idx" in attribute else None
            if "attribute_value_text" in attribute and attribute["attribute_value_text"]:
                self.attribute_value = attribute["attribute_value_text"]
            elif (
                "attribute_value_json_t9n" in attribute
                and attribute["attribute_value_json_t9n"]
                or self.feature_type == "JSON_T9N"
            ):
                self.attribute_value = convert_from_json(attribute["attribute_value_json_t9n"])
            elif "attribute_value_json" in attribute and attribute["attribute_value_json"]:
                self.attribute_value = convert_from_json(attribute["attribute_value_json"])
            elif "attribute_value" in attribute and attribute["attribute_value"]:
                self.attribute_value = attribute["attribute_value"]
            else:
                self.attribute_value = ""
            if self.feature_type == FeatureType.BOOL.value:
                self.attribute_value = bool_translate(self.attribute_value, language_iso2)
            if isinstance(self.attribute_value, Decimal):
                self.attribute_value = round(self.attribute_value, 2)
            self.extension = convert_from_json(attribute["extension"]) if "extension" in attribute else None


def attribute_collection(attributes: dict, asdict: bool = False, language_iso2: str = "pl") -> dict:
    attribute_col = {}
    for attribute_dict in attributes:
        attribute = Attribute(attribute=attribute_dict, language_iso2=language_iso2)
        a = attribute.asdict() if asdict else attribute
        if attribute.sku not in attribute_col:
            attribute_col[attribute.sku] = [a]
        else:
            attribute_col[attribute.sku].append(a)

    return attribute_col
