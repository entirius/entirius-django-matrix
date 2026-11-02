# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stock of a bundle as the cart counts it: checkout's get_bundle_quantities lays its count over the bundle's own
Stock row, in v2 `stock/`, v1 `stock/` and the on_stock read model. Checkout is not installed here, so its output
module is stood in for."""

import sys
import types
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from django_matrix.services import stock_service


@contextmanager
def checkout_output(bundle_quantities):
    """A checkout whose output.quantities.get_bundle_quantities answers `bundle_quantities` (None: too old to have it)."""
    output = types.ModuleType("django_checkout.output.quantities")
    if bundle_quantities is not None:
        output.get_bundle_quantities = MagicMock(return_value=bundle_quantities)
    modules = {
        "django_checkout": types.ModuleType("django_checkout"),
        "django_checkout.output": types.ModuleType("django_checkout.output"),
        "django_checkout.output.quantities": output,
    }
    with patch.dict(sys.modules, modules):
        yield getattr(output, "get_bundle_quantities", None)


class GetQuantitiesBundleTest(SimpleTestCase):
    @patch("django_matrix.services.stock_service._get_quantities", return_value={"BND": 15, "SKU": 3})
    def test_the_components_count_replaces_the_bundle_row(self, _):
        with checkout_output({"BND": 0}) as count:
            self.assertEqual(stock_service.get_quantities(["BND", "SKU"], "ch"), {"BND": 0, "SKU": 3})
        count.assert_called_once_with(["BND", "SKU"], "ch")

    @patch("django_matrix.services.stock_service._get_quantities", return_value={"SKU": 3})
    def test_a_bundle_without_its_own_row_is_still_answered(self, _):
        with checkout_output({"BND": 2}):
            self.assertEqual(stock_service.get_quantities(["BND", "SKU"], "ch"), {"BND": 2, "SKU": 3})

    @patch("django_matrix.services.stock_service._get_quantities", return_value={"BND": 15})
    def test_an_older_checkout_keeps_the_bundle_row(self, _):
        with checkout_output(None):
            self.assertEqual(stock_service.get_quantities(["BND"], "ch"), {"BND": 15})

    @patch("django_matrix.services.stock_service._get_quantities", return_value={"BND": 15, "SKU": 3})
    def test_v2_stock_reports_the_bundle_sold_out(self, _):
        with checkout_output({"BND": 0}):
            result = stock_service.get_stock_for_skus(["BND", "SKU"], "ch")
        self.assertEqual(result["BND"], {"quantity": 0, "is_in_stock": False})
        self.assertEqual(result["SKU"], {"quantity": 3, "is_in_stock": True})

    def test_v1_stock_gives_the_same_answer(self):
        from django_matrix.views.stock.listing import _get_quantities

        with patch.object(stock_service, "get_quantities", return_value={"BND": 0}) as service:
            self.assertEqual(_get_quantities(["BND"], "ch"), {"BND": 0})
        service.assert_called_once_with(["BND"], "ch")


class OnStockReadModelBundleTest(SimpleTestCase):
    def _worker(self, skus=None):
        from django_matrix.workers.fill_read_model_on_stock import FillReadModelOnStock

        worker = FillReadModelOnStock(channel=SimpleNamespace(idx="ch"))
        worker.skus = skus
        return worker

    @contextmanager
    def _checkout(self, rows, links, bundle_quantities):
        stock = MagicMock()
        stock.annotated.filter.return_value.values_list.return_value = rows
        checkout_models = types.ModuleType("django_checkout.models")
        checkout_models.Stock = stock
        bundle_link = MagicMock()
        bundle_link.objects.all.return_value.values_list.return_value = links
        pim_models = types.ModuleType("django_pim.models")
        pim_models.BundleLink = bundle_link
        modules = {"django_checkout.models": checkout_models, "django_pim.models": pim_models}
        if "django_pim" not in sys.modules:
            modules["django_pim"] = types.ModuleType("django_pim")
        with checkout_output(bundle_quantities) as count, patch.dict(sys.modules, modules):
            yield count

    def test_the_bundle_is_counted_as_the_cart_counts_it(self):
        rows = [("BND", 15), ("BED", 0), ("PILLOW", 9)]
        links = [("BND", "BED", 1), ("BND", "PILLOW", 2), ("BND", "PILLOW", 2)]
        with self._checkout(rows, links, {"BND": 0}) as count:
            self.assertEqual(self._worker().get_quantities_checkout(), {"BND": 0, "BED": 0, "PILLOW": 9})
        count.assert_called_once_with(["BND"], "ch")

    def test_a_pass_for_one_family_asks_only_its_bundles(self):
        links = [("BND", "BED", 1), ("OTHER", "BED", 1)]
        with self._checkout([("BND", 15)], links, {"BND": 4}) as count:
            self._worker(skus=["BND"]).get_quantities_checkout()
        count.assert_called_once_with(["BND"], "ch")
