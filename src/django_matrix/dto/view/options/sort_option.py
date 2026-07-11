# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class SortOption(DTO):
    position: int = 0
    label: str | None = None
    idx: str | None = None
    extension: str | None = None

    @staticmethod
    def factory(position, idx, label, extension=None):
        return SortOption(
            position=position,
            label=label or idx,
            idx=idx,
            extension=extension,
        )
