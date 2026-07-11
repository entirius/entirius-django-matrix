# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Alt-text language resolution in the pictures worker (featureset-cascade etap-05-extra).

Pure unit tests for ``_resolve_alt_text`` — no DB. They pin the new fallback contract:
requested language -> channel default language, and NOTHING else (the legacy magic
``"default"`` key is dead by PO decision 2026-06-11).
"""

from django_matrix.workers.fill_read_model_pictures_and_thumbs import _resolve_alt_text


def test_requested_language_wins_over_default():
    alt = {"en": "Red chair", "pl": "Czerwone krzesło"}

    assert _resolve_alt_text(alt, "pl", "en") == "Czerwone krzesło"


def test_missing_language_falls_back_to_channel_default():
    alt = {"en": "Red chair"}

    assert _resolve_alt_text(alt, "pl", "en") == "Red chair"


def test_no_lang_branch_uses_channel_default():
    alt = {"en": "Red chair", "pl": "Czerwone krzesło"}

    assert _resolve_alt_text(alt, None, "en") == "Red chair"


def test_legacy_default_key_is_dead():
    # Pre-etap-05-extra the worker honoured a magic "default" key nothing ever wrote.
    # It must no longer resolve — only real language codes count.
    alt = {"default": "Legacy alt"}

    assert _resolve_alt_text(alt, "pl", "en") is None
    assert _resolve_alt_text(alt, None, "en") is None


def test_empty_or_none_dict_is_none():
    assert _resolve_alt_text({}, "pl", "en") is None
    assert _resolve_alt_text(None, "pl", "en") is None


def test_empty_string_value_falls_through_to_default():
    alt = {"pl": "", "en": "Red chair"}

    assert _resolve_alt_text(alt, "pl", "en") == "Red chair"
