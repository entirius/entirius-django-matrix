# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_pim.models.product_picture import PictureRoleApiLabel, PictureRoleEnum

from django_matrix.dto import DTO


@dataclass
class SourceSet(DTO):
    source: str | None = None
    width: int | None = None
    height: int | None = None

    @staticmethod
    def factory(source: dict | None = None):
        if source is None:
            source = {}
        return SourceSet(
            source=source["source"] if "source" in source else None,
            width=source["width"] if "width" in source else None,
            height=source["height"] if "height" in source else None,
        )


@dataclass
class Picture(DTO):
    type: str = "picture"
    position: int = 0
    role: str | None = None
    source_set: list[SourceSet] | None = None
    alt_text: str | None = None

    @staticmethod
    def factory(picture: dict | None = None):
        if picture is None:
            picture = {}
        return Picture(
            position=picture["position"] if "position" in picture else 0,
            role=picture["role"] if "role" in picture else PictureRoleApiLabel.labelFromId(PictureRoleEnum.GENERAL),
            source_set=[SourceSet.factory(source=sr) for sr in picture["source_set"]],
            alt_text=picture.get("alt_text"),
        )


def pictures_collection(pictures: dict, asdict: bool = False) -> list[Picture]:
    pictures_col = []
    if pictures is None:
        return pictures_col
    for pictures_dict in pictures:
        picture = Picture.factory(pictures_dict)
        if asdict:
            pictures_col.append(picture.asdict())
        else:
            pictures_col.append(picture)
    return pictures_col
