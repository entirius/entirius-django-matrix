# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A per-product on-stock pass (what the PIM signals run) must keep a configurable's stock = sum of its children."""

import pytest

from django_matrix.models import ProductRepresentation
from django_matrix.workers import fill_read_model_on_stock as worker

STOCK = {"V2-CFG-001-S": 3, "V2-CFG-001-L": 0}

pytestmark = pytest.mark.skipif(not worker._HAS_QMS, reason="django_qms not enabled")


@pytest.fixture
def qms_stock(monkeypatch):
    monkeypatch.setattr(worker, "get_product_quantity", lambda channel_idx, sku: STOCK.get(sku, 0))


def _stock(sku):
    return ProductRepresentation.objects.filter(sku=sku).values_list("on_stock", "stock_qty").get()


@pytest.mark.parametrize("sku", ["V2-CFG-001", "V2-CFG-001-L"])
def test_pass_for_a_parent_or_a_child_sums_the_children(configurable_product, qms_stock, sku):
    worker.fill_read_model_on_stock_batch(channel=configurable_product.channel, product_id=sku)
    assert _stock("V2-CFG-001") == (True, 3)
    assert _stock("V2-CFG-001-S") == (True, 3) and _stock("V2-CFG-001-L") == (False, 0)


def test_pass_for_a_simple_product_touches_only_it(simple_product, configurable_product, qms_stock):
    worker.fill_read_model_on_stock_batch(channel=configurable_product.channel, product_id=simple_product.sku)
    assert _stock(simple_product.sku) == (False, 0)
    assert _stock("V2-CFG-001")[0] is True  # another family: untouched
