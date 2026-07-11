# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import ClassVar

from marshmallow import Schema
from marshmallow_dataclass import dataclass

from django_matrix.utils.params import SimpleQuery


@dataclass
class ProductUrlQuery(SimpleQuery):
    sku: list[str] | None = None
    url_key: list[str] | None = None

    Schema: ClassVar[type[Schema]] = Schema
