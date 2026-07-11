# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for numeric-feature unit conversion (mass / temperature / length).

DB-free. The helpers receive a PIM Unit class (as returned by
``Feature.get_cls_unit_conversion()``); these tests pass Mass/Temperature/Length
directly. Relies on django_pim default unit settings:
  mass: canonical g, "us" -> oz        temperature: canonical C, "us" -> F
  length: canonical mm, "us" -> inch   (other langs fall back to canonical)
"""

import pytest
from django_pim.workers.unit_conversion import Length, Mass, Temperature

from django_matrix.utils.unit_options import convert_bounds_for_lang, to_canonical


class TestConvertBoundsForLang:
    def test_mass_us_floors_min_ceils_max_in_ounces(self):
        # 1000 g -> 35.274 oz (floor 35); 5000 g -> 176.37 oz (ceil 177)
        low, high, unit = convert_bounds_for_lang(Mass, 1000.0, 5000.0, "us")
        assert (low, high, unit) == (35, 177, "oz")

    def test_mass_other_lang_stays_canonical_grams(self):
        low, high, unit = convert_bounds_for_lang(Mass, 1000.0, 5000.0, "pl")
        assert (low, high, unit) == (1000, 5000, "g")

    def test_temperature_us_returns_fahrenheit(self):
        # 0 C -> 32 F (floor 32); 100 C -> 212 F (ceil 212)
        low, high, unit = convert_bounds_for_lang(Temperature, 0.0, 100.0, "us")
        assert (low, high, unit) == (32, 212, "°F")

    def test_temperature_negative_lower_bound(self):
        low, high, unit = convert_bounds_for_lang(Temperature, -40.0, 100.0, "us")
        assert (low, high, unit) == (-40, 212, "°F")

    def test_temperature_other_lang_stays_celsius(self):
        low, high, unit = convert_bounds_for_lang(Temperature, 0.0, 100.0, "en")
        assert (low, high, unit) == (0, 100, "°C")

    def test_length_us_returns_inches(self):
        # 1000 mm -> 39.3701 inch -> ceil 40
        low, high, unit = convert_bounds_for_lang(Length, 0.0, 1000.0, "us")
        assert (low, high, unit) == (0, 40, "inch")


class TestBoundsEncloseDataAfterRoundTrip:
    """The core C1 guarantee: slider bounds, sent back and converted to canonical by the
    range filter, must still enclose the real min/max so the extreme products pass an
    inclusive (>= / <=) filter."""

    @pytest.mark.parametrize("unit_cls,lo,hi", [(Mass, 1000.0, 5000.0), (Temperature, -40.0, 100.0)])
    def test_round_trip_encloses(self, unit_cls, lo, hi):
        display_low, display_high, _ = convert_bounds_for_lang(unit_cls, lo, hi, "us")
        assert to_canonical(unit_cls, display_low, "us") <= lo
        assert to_canonical(unit_cls, display_high, "us") >= hi


class TestToCanonical:
    def test_temperature_fahrenheit_back_to_celsius(self):
        assert to_canonical(Temperature, 212.0, "us") == pytest.approx(100.0)

    def test_mass_ounces_back_to_grams(self):
        assert to_canonical(Mass, 35.274, "us") == pytest.approx(1000.0, rel=1e-4)

    def test_other_lang_is_noop(self):
        assert to_canonical(Mass, 500.0, "pl") == pytest.approx(500.0)
