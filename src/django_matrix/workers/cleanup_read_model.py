# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django_pim.models import Product

from django_matrix.models import Channel, ProductRepresentation


def cleanup_read_model(channel: Channel):
    products_representation: list[ProductRepresentation] = ProductRepresentation.objects.filter(channel=channel)

    for pr in products_representation:
        try:
            product: Product = Product.objects.get(real_product__sku=pr.sku, shop__idx=channel.idx)
            if not product.is_enabled:
                pr.delete()
        except ObjectDoesNotExist:
            pr.delete()
