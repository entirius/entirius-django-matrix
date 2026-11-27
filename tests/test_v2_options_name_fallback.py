# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""options/ names fall back: requested language -> channel default language -> en -> idx."""

import pytest

BASE = "/api/matrix/v2/test-v2/options/"


def _language(iso2: str, iso3: str):
    from django_regional.models import Language

    lang, _ = Language.objects.get_or_create(
        iso2=iso2, defaults={"iso3": iso3, "name_en": iso2, "name_pl": iso2, "name_source": iso2}
    )
    return lang


@pytest.fixture
def make_filters(channel_full):
    """Create a SELECT feature (filterable + sortable) with one attribute; return the channel."""
    from django_pim.models import Attribute, Feature, FeatureTypeEnum, FilterTypeEnum

    from django_matrix.models import FilterableFeatures, SortableFeatures

    ch = channel_full[0]
    for iso2, iso3 in (("pl", "pol"), ("de", "deu"), ("fr", "fra")):
        _language(iso2, iso3)

    def make(feature_names: dict, attribute_names: dict) -> None:
        feature = Feature.objects.create(
            idx="series",
            name_t9n=feature_names,
            feature_type=FeatureTypeEnum.SELECT,
            filter_type=FilterTypeEnum.DEFAULT,
            is_filterable=True,
            display_order=1,
        )
        Attribute.objects.create(feature=feature, idx="anvora", name_t9n=attribute_names, display_order=1)
        FilterableFeatures.objects.create(channel=ch, feature=feature, position=1)
        SortableFeatures.objects.create(channel=ch, feature=feature, position=1)

    return make


def _get(api, language: str) -> dict:
    response = api.get(f"{BASE}?language={language}&currency=EUR&country=PL")
    assert response.status_code == 200
    return response.json()


def _group(data: dict) -> dict:
    return next(f for f in data["filters"] if f["idx"] == "series")


class TestOptionsNameFallback:
    def test_requested_language_wins(self, api, make_filters):
        make_filters({"en": "Series", "pl": "Seria"}, {"en": "Anvora", "pl": "Anwora"})
        group = _group(_get(api, "pl"))
        assert group["label"] == "Seria"
        assert group["values"][0]["label"] == "Anwora"

    def test_missing_translation_falls_back_to_en(self, api, make_filters):
        make_filters({"en": "Series"}, {"en": "Anvora"})
        data = _get(api, "pl")
        assert _group(data)["label"] == "Series"
        assert _group(data)["values"][0]["label"] == "Anvora"

    def test_empty_translation_counts_as_missing(self, api, make_filters):
        make_filters({"en": "Series", "pl": ""}, {"en": "Anvora", "pl": ""})
        group = _group(_get(api, "pl"))
        assert group["label"] == "Series"
        assert group["values"][0]["label"] == "Anvora"

    def test_channel_default_language_before_en(self, api, make_filters, channel_full):
        ch = channel_full[0]
        ch.default_language = _language("de", "deu")
        ch.save()
        make_filters({"en": "Series", "de": "Serie"}, {"en": "Anvora", "de": "Anvora DE"})
        group = _group(_get(api, "fr"))
        assert group["label"] == "Serie"
        assert group["values"][0]["label"] == "Anvora DE"

    def test_nothing_translated_falls_back_to_idx(self, api, make_filters):
        make_filters({}, {})
        data = _get(api, "pl")
        assert _group(data)["label"] == "series"
        assert _group(data)["values"][0]["label"] == "anvora"


class TestSortableFeatureNameFallback:
    """Sort labels come from get_comparable_features (sort needs product values, so call it directly)."""

    @pytest.mark.parametrize(
        ("names", "expected"),
        [({"en": "Series", "pl": "Seria"}, "Seria"), ({"en": "Series"}, "Series"), ({}, "series")],
    )
    def test_sort_label_chain(self, make_filters, channel_full, names, expected):
        from django_matrix.repository.raw_sql.options import Options

        make_filters(names, {})
        ch, _, currency, country = channel_full
        pl = _language("pl", "pol")
        options = Options(params=None, channel=ch, language=pl, currency=currency, country=country)
        (feature,) = options.get_comparable_features(channel=ch, language=pl)
        assert feature.feature_name == expected
