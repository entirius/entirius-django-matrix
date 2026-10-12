# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Optional sibling apps that are installed but not in INSTALLED_APPS.

Importing the models of such an app raises RuntimeError, not ImportError, so every guard around
an optional sibling has to catch both.
"""

import ast
import builtins
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import django_matrix

SRC = Path(django_matrix.__file__).parent
SIBLINGS = {"django_pricemanager", "django_qms", "django_checkout", "django_omnibus", "django_reviews"}
EXEMPT = {"signals/receivers.py"}  # imports django_checkout.signals.signals: signals only, no models


def _imports_sibling(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.ImportFrom):
        names = [stmt.module or ""]
    elif isinstance(stmt, ast.Import):
        names = [alias.name for alias in stmt.names]
    else:
        return False
    return any(name.split(".")[0] in SIBLINGS for name in names)


def _catches_runtime_error(node: ast.Try) -> bool:
    for handler in node.handlers:
        if handler.type is None:
            return True
        caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        if any(isinstance(exc, ast.Name) and exc.id in {"RuntimeError", "Exception"} for exc in caught):
            return True
    return False


def _guards_missing_runtime_error() -> list[str]:
    missing = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).as_posix()
        if relative in EXEMPT:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Try) and any(map(_imports_sibling, node.body)) and not _catches_runtime_error(node):
                missing.append(f"{relative}:{node.lineno}")
    return missing


def test_sibling_guards_catch_runtime_error():
    assert _guards_missing_runtime_error() == []


@pytest.fixture
def disable_app(monkeypatch):
    """Make imports of one sibling fail the way an installed app outside INSTALLED_APPS does."""

    def _disable(prefix: str) -> None:
        real_import = builtins.__import__

        def _import(name, *args, **kwargs):
            if name == prefix or name.startswith(f"{prefix}."):
                raise RuntimeError(f"{name} isn't in an application in INSTALLED_APPS")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _import)

    return _disable


@pytest.mark.parametrize(
    ("module_name", "sibling", "flag"),
    [
        ("django_matrix.workers.fill_read_model_prices", "django_pricemanager", "_HAS_PRICEMANAGER"),
        ("django_matrix.workers.fill_read_model_on_stock", "django_qms", "_HAS_QMS"),
    ],
)
def test_worker_imports_without_its_sibling(monkeypatch, disable_app, module_name, sibling, flag):
    module = importlib.import_module(module_name)
    try:
        disable_app(sibling)
        importlib.reload(module)
        assert getattr(module, flag) is False
    finally:
        monkeypatch.undo()
        importlib.reload(module)


def test_bundle_stock_quantities_empty_without_checkout(disable_app):
    from django_matrix.views.products.bundle import _get_stock_quantities

    disable_app("django_checkout")

    assert _get_stock_quantities(SimpleNamespace(idx="default"), ["X"]) == {}
