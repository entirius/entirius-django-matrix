# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_pim.models.product_video import VideoRoleApiLabel, VideoRoleEnum

from django_matrix.dto import DTO


@dataclass
class SourceSet(DTO):
    title: str | None = None
    url: str | None = None
    source: str | None = None

    @staticmethod
    def factory(source: dict | None = None):
        if source is None:
            source = {}
        return SourceSet(
            title=source["title"] if "title" in source else None,
            url=source["url"] if "url" in source else None,
            source=source["source"] if "source" in source else None,
        )


@dataclass
class Video(DTO):
    type: str = "video"
    position: int = 0
    role: str | None = None
    source_set: list[SourceSet] | None = None

    @staticmethod
    def factory(video: dict | None = None):
        if video is None:
            video = {}
        return Video(
            position=video["position"] if "position" in video else 0,
            role=video["role"] if "role" in video else VideoRoleApiLabel.labelFromId(VideoRoleEnum.MAIN),
            source_set=[SourceSet.factory(source=sr) for sr in video["source_set"]],
        )


def videos_collection(videos: dict, asdict: bool = False) -> list[Video]:
    videos_col = []
    if videos is None:
        return videos_col
    for videos_dict in videos:
        video = Video.factory(videos_dict)
        if asdict:
            videos_col.append(video.asdict())
        else:
            videos_col.append(video)
    return videos_col
