# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import asdict, dataclass

from django_matrix.dto import DTO

from .filter_option import FilterOption
from .sort_option import SortOption


@dataclass
class FilterGroup(DTO):
    position: int = 0
    label: str | None = None
    idx: str | None = None
    filter_type: str | None = None
    options: list[FilterOption | SortOption] | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None

    @staticmethod
    def factory(position, idx, filter_type, options, label=None, min_value=None, max_value=None, unit=None):
        return FilterGroup(
            position=position,
            idx=idx,
            label=label or idx,
            filter_type=filter_type,
            options=options,
            min_value=min_value,
            max_value=max_value,
            unit=unit,
        )

    def asdict(self):
        result = asdict(self)
        if self.min_value is None:
            result.pop("min_value", None)
        if self.max_value is None:
            result.pop("max_value", None)
        if self.options is None:
            result.pop("options", None)
        if self.unit is None:
            result.pop("unit", None)
        return result
