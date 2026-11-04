# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# idx_product_channel_stock_id starts with the same two columns, so it serves every query this index did.
# A separate migration from 0047: a failed drop re-runs on its own, without rebuilding the new index.

from django.contrib.postgres.operations import RemoveIndexConcurrently
from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("django_matrix", "0047_productrepresentation_idx_product_channel_stock_id"),
    ]

    operations = [
        RemoveIndexConcurrently(model_name="productrepresentation", name="idx_product_channel_stock"),
    ]
