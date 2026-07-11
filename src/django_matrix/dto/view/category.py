# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class Breadcrumb(DTO):
    name: str
    url_key: str | None


@dataclass
class Category(DTO):
    idx: str
    name: str
    url_key: str | None
    tree_deep: int
    position: int
    sku: str | None = None
    has_children: bool = False
    products_count: int = 0
    parent_idx: str | None = None
    external_id: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    description: str | None = None
    rich_content: dict | None = None
    pictures: list | None = None
    breadcrumb_path: str | None = None
    breadcrumbs: list[Breadcrumb] | None = None
