# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Verify soft dependency patterns in django-matrix source code.

Tests that pricemanager and qms are optional:
- No top-level hard imports that crash on missing deps
- Sentinel flags detect availability
- Workers early-return when deps absent
- Bundle price method returns empty gracefully
"""

import inspect

import pytest


def test_prices_type_checking_guard():
    """orm/prices.py uses TYPE_CHECKING for Price import, no runtime crash."""
    import django_matrix.repository.orm.prices

    src = inspect.getsource(django_matrix.repository.orm.prices)
    assert "from __future__ import annotations" in src
    assert "if TYPE_CHECKING:" in src
    before_guard = src.split("if TYPE_CHECKING:")[0]
    assert "from django_pricemanager.models import Price" not in before_guard


def test_bundle_method_lazy_import():
    """bundle method has try/except ImportError returning empty tuple."""
    from django_matrix.repository.orm.prices import Prices

    src = inspect.getsource(Prices.get_product_bundle_components_price)
    assert "try:" in src
    assert "ImportError" in src
    assert 'return [], ""' in src


def test_pricemanager_sentinel():
    """fill_read_model_prices has _HAS_PRICEMANAGER sentinel, no raise."""
    try:
        import django_matrix.workers.fill_read_model_prices
    except RuntimeError:
        pytest.skip("django_pricemanager not in INSTALLED_APPS")

    src = inspect.getsource(django_matrix.workers.fill_read_model_prices)
    assert "_HAS_PRICEMANAGER = True" in src
    assert "_HAS_PRICEMANAGER = False" in src
    assert 'raise Exception("django_matrix does not have access to django_pricemanager' not in src
    assert "if not _HAS_PRICEMANAGER:" in src


def test_qms_sentinel():
    """fill_read_model_on_stock has _HAS_QMS sentinel, no raise."""
    try:
        import django_matrix.workers.fill_read_model_on_stock
    except RuntimeError:
        pytest.skip("django_qms not in INSTALLED_APPS")

    src = inspect.getsource(django_matrix.workers.fill_read_model_on_stock)
    assert "_HAS_QMS = True" in src
    assert "_HAS_QMS = False" in src
    assert 'raise Exception("django_matrix does not have access to django_qms' not in src
    assert "if not _HAS_QMS:" in src
    assert "if not process_checkout and not _HAS_QMS:" in src


def test_tasks_lazy_imports():
    """tasks.py has no top-level imports for price/stock workers."""
    import django_matrix.tasks

    src = inspect.getsource(django_matrix.tasks)
    toplevel = src.split("def fill_read_model_with_flags")[0]
    assert "from django_matrix.workers.fill_read_model_prices" not in toplevel
    assert "from django_matrix.workers.fill_read_model_on_stock" not in toplevel
    assert "from django_matrix.workers.fill_read_model_prices import fill_read_model_prices" in src
    assert "from django_matrix.workers.fill_read_model_on_stock import fill_read_model_on_stock_batch" in src


def test_custom_details_guard():
    """custom_details has try/except ImportError with clear message."""
    from django_matrix.repository.raw_sql.custom_details import CustomDetails

    src = inspect.getsource(CustomDetails.get_attributes_details)
    assert "try:" in src
    assert "ImportError" in src
    assert "Custom product pricing requires django_pricemanager" in src


def test_no_settings_flags():
    """No MATRIX_PRICES_ENABLED or MATRIX_STOCK_ENABLED in settings."""
    from django_matrix import settings as ms

    assert not hasattr(ms, "MATRIX_PRICES_ENABLED")
    assert not hasattr(ms, "MATRIX_STOCK_ENABLED")


def test_fuzzy_search_settings_defaults():
    """Fuzzy search settings have correct defaults."""
    from django_matrix import settings as ms

    assert ms.MATRIX_FUZZY_SEARCH is False
    assert ms.MATRIX_FUZZY_SEARCH_THRESHOLD == 0.35


def test_deprecated_on_stock_function_removed():
    """Deprecated fill_read_model_on_stock (with ProcessLoger typo) is removed."""
    try:
        import django_matrix.workers.fill_read_model_on_stock
    except RuntimeError:
        pytest.skip("django_qms not in INSTALLED_APPS")

    src = inspect.getsource(django_matrix.workers.fill_read_model_on_stock)
    assert "ProcessLoger" not in src
    assert "def fill_read_model_on_stock(channel: Channel):" not in src


def test_backward_compat_sentinels_true():
    """With deps installed, sentinels are True (backward compatible)."""
    try:
        from django_matrix.workers.fill_read_model_prices import _HAS_PRICEMANAGER

        assert _HAS_PRICEMANAGER is True
    except (ImportError, RuntimeError):
        pytest.skip("django_pricemanager not in INSTALLED_APPS")

    try:
        from django_matrix.workers.fill_read_model_on_stock import _HAS_QMS

        assert _HAS_QMS is True
    except (ImportError, RuntimeError):
        pytest.skip("django_qms not in INSTALLED_APPS")
