# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

try:
    from django_pim.models import Feature
except ImportError:
    raise Exception("django_matrix does not have access to django_pim module")

from django_matrix.enums import FeatureType


def get_feature_type(feature_idx: str):
    feature = Feature.objects.get(idx=feature_idx)
    return FeatureType.map(feature.feature_type)


def get_feature(feature_idx: str):
    return Feature.objects.get(idx=feature_idx)
