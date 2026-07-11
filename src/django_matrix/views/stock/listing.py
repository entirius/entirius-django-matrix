# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import ClassVar

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response
from marshmallow import Schema
from marshmallow_dataclass import dataclass as ma_dataclass

from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import SimpleQuery, get_view_variable_from_kwargs


@ma_dataclass
class StockQuery(SimpleQuery):
    sku: list[str] | None = None
    Schema: ClassVar[type[Schema]] = Schema


def _quantity_factory(sku: str, quantity: int) -> dict:
    is_in_stock = quantity > 0
    return {
        "sku": sku,
        "quantity": quantity,
        "is_in_stock": is_in_stock,
        "label": "In stock" if is_in_stock else "Out of stock",
        "shipping_date": "",
    }


def _get_quantities(skus: list[str], channel_idx: str) -> dict:
    """Get stock quantities, trying checkout first, then QMS."""
    try:
        from django_checkout.models import Stock

        quantities = {}
        stock_data = Stock.annotated.filter(product__sku__in=skus, product__channel__idx=channel_idx).values(
            "product__sku", "saleable_quantity"
        )
        for row in stock_data:
            quantities[row["product__sku"]] = row["saleable_quantity"]
        return quantities
    except ImportError:
        pass

    try:
        from django_qms.output import get_quantities

        return dict(get_quantities(channel_idx).filter(product__sku__in=skus))
    except ImportError:
        pass

    return {}


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(StockQuery.Schema())
@prepare_view
def stock_listing_view(request, params: StockQuery, *args, **kwargs) -> "Response":
    """Returns stock quantities for one or more SKUs."""
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)

    if not params.sku:
        return Response({})

    quantities = _get_quantities(params.sku, channel.idx)
    result = {}
    for sku in params.sku:
        qty = quantities.get(sku, 0)
        result[sku] = _quantity_factory(sku, qty)

    return Response(result)


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(SimpleQuery.Schema())
@prepare_view
def stock_details_view(request, params: SimpleQuery, sku=None, *args, **kwargs) -> "Response":
    """Returns stock quantity for a single SKU."""
    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)

    quantities = _get_quantities([sku], channel.idx)
    qty = quantities.get(sku)
    if qty is None:
        raise NotFound(f"No stock data for SKU: {sku}")

    return Response(_quantity_factory(sku, qty))
