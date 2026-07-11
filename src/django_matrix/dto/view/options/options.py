# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

from django_matrix.dto import DTO


@dataclass
class ComparableFeature(DTO):
    feature_idx: str | None = None
    feature_name: str | None = None
    position: int = 0

    @staticmethod
    def factory(feature: dict | None = None):
        if feature is None:
            feature = {}
        return ComparableFeature(
            feature_idx=feature["feature_idx"] if "feature_idx" in feature else None,
            feature_name=feature["feature_name"] if "feature_name" in feature else None,
            position=feature["position"] if "position" in feature else 0,
        )

    def comparable_features_collection(features: list, asdict: bool = False):
        features_col = []
        if features is None:
            return features_col
        for feature_dict in features:
            feature = ComparableFeature.factory(feature_dict)
            if asdict:
                features_col.append(feature.asdict())
            else:
                features_col.append(feature)
        return features_col
