# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit conversion helpers for numeric (mass/temperature/length) feature options.

The read model stores the raw ``ProductAttribute.value_decimal`` from PIM (the feature's
*canonical*/default unit) in ``ProductRepresentation.attributes_filter[feature_idx]`` as a
list, like DECIMAL. The storefront sees values in the unit configured for its language, so:

- options endpoint converts canonical -> display unit (``convert_bounds_for_lang``)
- listing range filter converts display unit -> canonical (``to_canonical``)

The Unit class (Mass / Temperature / Length) and its canonical unit are resolved by
PIM's ``Feature.get_cls_unit_conversion()`` -- the single source of truth for the
feature_type -> unit mapping -- and passed in here. These helpers only adapt PIM's
conversion math to the read model's needs: producing widened slider bounds in the display
unit and the reverse direction (display -> canonical), neither of which PIM exposes. The
conversion math itself lives in ``django_pim.workers.unit_conversion``.
"""

import math

from django_pim.settings import UNIT_CONVERSION_DECIMAL_PLACES, UNIT_SIGN_MAPPING


def _int_if_whole(value: float) -> float:
    return int(value) if float(value).is_integer() else value


def convert_bounds_for_lang(unit_cls, min_value: float, max_value: float, lang: str) -> tuple[float, float, str]:
    """Convert a canonical [min, max] range to the language's display unit + unit sign."""
    canonical_unit = unit_cls.default_unit
    target_unit = unit_cls.lang_mapping.get(lang, canonical_unit)
    sign, decimal_places = UNIT_SIGN_MAPPING.get(target_unit, (target_unit, UNIT_CONVERSION_DECIMAL_PLACES))
    factor = 10**decimal_places
    low = math.floor(unit_cls(min_value, canonical_unit).convert(target_unit) * factor) / factor
    high = math.ceil(unit_cls(max_value, canonical_unit).convert(target_unit) * factor) / factor
    return _int_if_whole(low), _int_if_whole(high), str(sign)


def to_canonical(unit_cls, value: float, lang: str) -> float:
    """Value in the language's display unit -> canonical (stored) value for SQL comparison."""
    canonical_unit = unit_cls.default_unit
    target_unit = unit_cls.lang_mapping.get(lang, canonical_unit)
    obj = unit_cls(value, canonical_unit)
    obj.setValue(value, target_unit)
    return obj.convert(canonical_unit)
