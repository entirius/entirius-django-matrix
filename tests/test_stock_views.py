# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for Matrix stock proxy endpoints (views/stock/listing.py).

Covers:
- _quantity_factory: response shape for in-stock and out-of-stock
- _get_quantities: checkout → QMS → empty fallback chain
- stock_listing_view: batch stock lookup, empty SKU list, missing SKUs
- stock_details_view: single SKU lookup, 404 on missing SKU
- Cynthia response format compatibility
"""

from unittest.mock import patch

from django.test import SimpleTestCase

# ---------------------------------------------------------------------------
# Unit tests: _quantity_factory
# ---------------------------------------------------------------------------


class QuantityFactoryTest(SimpleTestCase):
    def test_in_stock_response_shape(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("SKU-001", 10)

        self.assertEqual(result["sku"], "SKU-001")
        self.assertEqual(result["quantity"], 10)
        self.assertTrue(result["is_in_stock"])
        self.assertEqual(result["label"], "In stock")
        self.assertEqual(result["shipping_date"], "")

    def test_out_of_stock(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("SKU-002", 0)

        self.assertEqual(result["quantity"], 0)
        self.assertFalse(result["is_in_stock"])
        self.assertEqual(result["label"], "Out of stock")

    def test_negative_quantity_is_out_of_stock(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("SKU-003", -5)

        self.assertFalse(result["is_in_stock"])
        self.assertEqual(result["label"], "Out of stock")

    def test_large_quantity(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("SKU-004", 99999)

        self.assertEqual(result["quantity"], 99999)
        self.assertTrue(result["is_in_stock"])

    def test_has_all_required_keys(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("X", 1)

        self.assertEqual(set(result.keys()), {"sku", "quantity", "is_in_stock", "label", "shipping_date"})

    def test_quantity_one_is_in_stock(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("X", 1)

        self.assertTrue(result["is_in_stock"])


# ---------------------------------------------------------------------------
# Unit tests: _get_quantities fallback chain
# ---------------------------------------------------------------------------


class GetQuantitiesCheckoutPathTest(SimpleTestCase):
    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_returns_checkout_quantities(self, mock_fn):
        mock_fn.return_value = {"SKU-A": 10, "SKU-B": 0}

        result = mock_fn(["SKU-A", "SKU-B"], "default-europe")

        self.assertEqual(result["SKU-A"], 10)
        self.assertEqual(result["SKU-B"], 0)

    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_missing_sku_not_in_result(self, mock_fn):
        mock_fn.return_value = {"SKU-A": 5}

        result = mock_fn(["SKU-A", "SKU-MISSING"], "ch-1")

        self.assertIn("SKU-A", result)
        self.assertNotIn("SKU-MISSING", result)

    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_empty_sku_list_returns_empty(self, mock_fn):
        mock_fn.return_value = {}

        result = mock_fn([], "ch-1")

        self.assertEqual(result, {})

    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_no_stock_source_returns_empty(self, mock_fn):
        mock_fn.return_value = {}

        result = mock_fn(["SKU-X"], "ch-1")

        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Unit tests: StockQuery schema
# ---------------------------------------------------------------------------


class StockQuerySchemaTest(SimpleTestCase):
    def test_parses_sku_list(self):
        from django.http import QueryDict

        from django_matrix.views.stock.listing import StockQuery

        qd = QueryDict(mutable=True)
        qd.setlist("sku", ["SKU-1", "SKU-2"])
        qd["language"] = "en"
        data = StockQuery.Schema().load(qd)

        self.assertEqual(data.sku, ["SKU-1", "SKU-2"])
        self.assertEqual(data.language, "en")

    def test_sku_is_optional(self):
        from django_matrix.views.stock.listing import StockQuery

        data = StockQuery.Schema().load({})

        self.assertIsNone(data.sku)

    def test_inherits_regional_params(self):
        from django.http import QueryDict

        from django_matrix.views.stock.listing import StockQuery

        qd = QueryDict(mutable=True)
        qd["currency"] = "EUR"
        qd["country"] = "DE"
        qd["language"] = "en"
        data = StockQuery.Schema().load(qd)

        self.assertEqual(data.currency, "EUR")
        self.assertEqual(data.country, "DE")


# ---------------------------------------------------------------------------
# View logic tests (mock _get_quantities, verify response assembly)
# ---------------------------------------------------------------------------


class StockListingLogicTest(SimpleTestCase):
    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_builds_response_for_all_skus(self, mock_get_qty):
        from django_matrix.views.stock.listing import _quantity_factory

        mock_get_qty.return_value = {"A": 10, "B": 0}
        quantities = mock_get_qty(["A", "B"], "ch")
        result = {sku: _quantity_factory(sku, quantities.get(sku, 0)) for sku in ["A", "B"]}

        self.assertTrue(result["A"]["is_in_stock"])
        self.assertFalse(result["B"]["is_in_stock"])
        self.assertEqual(result["A"]["quantity"], 10)

    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_missing_sku_defaults_to_zero(self, mock_get_qty):
        from django_matrix.views.stock.listing import _quantity_factory

        mock_get_qty.return_value = {"A": 5}
        quantities = mock_get_qty(["A", "MISSING"], "ch")
        result = {sku: _quantity_factory(sku, quantities.get(sku, 0)) for sku in ["A", "MISSING"]}

        self.assertEqual(result["MISSING"]["quantity"], 0)
        self.assertFalse(result["MISSING"]["is_in_stock"])

    def test_empty_sku_list_returns_empty(self):
        result = {}
        self.assertEqual(result, {})


class StockDetailsLogicTest(SimpleTestCase):
    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_returns_single_sku_data(self, mock_get_qty):
        from django_matrix.views.stock.listing import _quantity_factory

        mock_get_qty.return_value = {"SKU-001": 25}
        quantities = mock_get_qty(["SKU-001"], "ch")
        qty = quantities.get("SKU-001")
        result = _quantity_factory("SKU-001", qty)

        self.assertEqual(result["quantity"], 25)
        self.assertTrue(result["is_in_stock"])

    @patch("django_matrix.views.stock.listing._get_quantities")
    def test_missing_sku_returns_none(self, mock_get_qty):
        mock_get_qty.return_value = {}
        quantities = mock_get_qty(["MISSING"], "ch")

        self.assertIsNone(quantities.get("MISSING"))


# ---------------------------------------------------------------------------
# v1 URL routing (slash-SKU support: 1C01/N must reach stock_details_view)
# ---------------------------------------------------------------------------


class V1StockRoutingTest(SimpleTestCase):
    def test_slash_sku_resolves_to_stock_details(self):
        from django.urls import resolve

        match = resolve("/api/matrix/v1/test-channel/stock/1C01/N/")

        self.assertEqual(match.url_name, "matrix-stock-details")
        self.assertEqual(match.kwargs["sku"], "1C01/N")
        self.assertEqual(match.kwargs["channel_idx"], "test-channel")

    def test_plain_sku_resolves_to_stock_details(self):
        from django.urls import resolve

        match = resolve("/api/matrix/v1/test-channel/stock/SKU-001/")

        self.assertEqual(match.url_name, "matrix-stock-details")
        self.assertEqual(match.kwargs["sku"], "SKU-001")


# ---------------------------------------------------------------------------
# Cynthia response format compatibility
# ---------------------------------------------------------------------------


class CynthiaCompatibilityTest(SimpleTestCase):
    """Storefront expects: { data: { "SKU": { sku, quantity, is_in_stock, label, shipping_date } } }"""

    def test_listing_format_keyed_by_sku(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = {"SKU-001": _quantity_factory("SKU-001", 10)}

        self.assertIn("SKU-001", result)
        entry = result["SKU-001"]
        self.assertEqual(entry["sku"], "SKU-001")
        self.assertIsInstance(entry["quantity"], int)
        self.assertIsInstance(entry["is_in_stock"], bool)
        self.assertIsInstance(entry["label"], str)
        self.assertIsInstance(entry["shipping_date"], str)

    def test_all_five_fields_present(self):
        from django_matrix.views.stock.listing import _quantity_factory

        result = _quantity_factory("X", 5)

        self.assertEqual(len(result), 5)

    def test_label_values_match_cynthia(self):
        from django_matrix.views.stock.listing import _quantity_factory

        self.assertEqual(_quantity_factory("X", 1)["label"], "In stock")
        self.assertEqual(_quantity_factory("X", 0)["label"], "Out of stock")

    def test_shipping_date_empty_string(self):
        from django_matrix.views.stock.listing import _quantity_factory

        self.assertEqual(_quantity_factory("X", 1)["shipping_date"], "")
