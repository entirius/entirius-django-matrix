# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# The default listing orders by (on_stock, id); this index serves that order without sorting the channel.
# CONCURRENTLY keeps the table writable while the index builds, which needs a migration outside a transaction.

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("django_matrix", "0001_squashed_0046_alter_attribute_attribute_value_text"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="productrepresentation",
            index=models.Index(fields=["channel", "on_stock", "id"], name="idx_product_channel_stock_id"),
        ),
    ]
