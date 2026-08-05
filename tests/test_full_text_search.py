# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Full-text search plumbing — text search config resolution and tsquery building.

Both paths are only reachable with MATRIX_FULL_TEXT_SEARCH enabled, and both used to turn a
plain request into an unauthenticated HTTP 500.
"""

import pytest

from django_matrix.repository.raw_sql import (
    FALLBACK_TEXT_SEARCH_CONFIG,
    DbConnect,
    _tsquery_lexemes,
    get_text_search_configs,
)

BASE = "/api/matrix/v2/test-v2/products/"
SEARCH = "/api/matrix/v2/test-v2/search/"


class TestTextSearchConfig:
    """`Language.name_en` is admin-editable and gets interpolated into SQL."""

    def test_known_language_maps_to_its_config(self, db):
        assert DbConnect().get_full_text_search_lang(_language("en", "english")) == "english"

    def test_language_postgres_does_not_know_falls_back(self, db):
        """Polish is a real market language and is not a Postgres text search configuration."""
        assert "polish" not in get_text_search_configs()
        assert DbConnect().get_full_text_search_lang(_language("pl", "polish")) == FALLBACK_TEXT_SEARCH_CONFIG

    def test_no_language_falls_back(self, db):
        assert DbConnect().get_full_text_search_lang(None) == FALLBACK_TEXT_SEARCH_CONFIG

    def test_name_is_case_insensitive(self, db):
        assert DbConnect().get_full_text_search_lang(_language("en", "English")) == "english"

    def test_injection_attempt_falls_back(self, db):
        """The config name is interpolated, so an unknown value must never reach the SQL string."""
        hostile = _language("xx", "simple', 'x') || (SELECT version()) --")
        assert DbConnect().get_full_text_search_lang(hostile) == FALLBACK_TEXT_SEARCH_CONFIG

    def test_config_names_are_shape_checked(self, db):
        """Even coming from pg_ts_config the name is interpolated, so it must be an identifier."""
        assert all(name.replace("_", "").isalnum() for name in get_text_search_configs())


class TestTsqueryLexemes:
    """to_tsquery rejects operators outright — an allowlist is the only safe split."""

    def test_words_become_prefix_lexemes(self):
        assert _tsquery_lexemes("red sofa") == ["red", "sofa"]

    def test_hyphens_are_kept(self):
        assert _tsquery_lexemes("ENT-S001") == ["ENT-S001"]

    @pytest.mark.parametrize("term", ["<", ">", "*", '"', "\\", "a & b", "a | b", "!x", "(y)", "z:", "a <-> b"])
    def test_operators_never_survive(self, term):
        assert all(ch not in lexeme for lexeme in _tsquery_lexemes(term) for ch in '<>*"\\&|!():')

    def test_apostrophes_are_not_doubled(self):
        """The value is a bound param — doubling quotes corrupted the search term."""
        assert _tsquery_lexemes("O'Brien") == ["O", "Brien"]

    def test_operator_only_input_yields_nothing(self):
        assert _tsquery_lexemes("&|!()") == []

    def test_builds_and_within_phrase_or_between(self, db):
        _, param, value = DbConnect().prepare_tsquery(["red sofa", "chair"], None)
        assert param == "ts_search_str"
        assert value == "(red:* & sofa:*) | (chair:*)"

    def test_unparseable_phrase_is_dropped(self, db):
        _, _, value = DbConnect().prepare_tsquery(["&&&", "chair"], None)
        assert value == "(chair:*)"


class TestFtsEndToEnd:
    """With FTS on, these used to be one-request 500s."""

    def test_polish_language_does_not_500(self, api, simple_product, searchable_channel, fts_on):
        response = api.get(f"{BASE}?language=pl&currency=EUR&country=PL&search=chair")
        assert response.status_code == 200

    @pytest.mark.parametrize("term", ["<", "a<->b", 'say"what', "back\\slash", "*"])
    def test_operator_terms_do_not_500(self, api, simple_product, searchable_channel, fts_on, term):
        response = api.get(f"{SEARCH}?language=en&currency=EUR&country=PL&q={term}chair")
        assert response.status_code == 200

    def test_search_still_matches_with_fts_on(self, api, simple_product, searchable_channel, fts_on):
        results = api.get(f"{BASE}?language=en&currency=EUR&country=PL&search=chair").json()["results"]
        assert [r["sku"] for r in results] == ["V2-SIMPLE-001"]


def _language(iso2: str, name_en: str):
    from django_regional.models import Language

    return Language(iso2=iso2, name_en=name_en, iso3=iso2 * 3, name_pl=name_en, name_source=name_en)
