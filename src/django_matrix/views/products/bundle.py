# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Prefetch
from django_pim.services.bundle_data import get_bundle_limits, get_bundle_subproducts
from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import NotFound
from django_utils.api.responses import Response

from django_matrix.dto.view.picture import pictures_collection
from django_matrix.dto.view.price import price_collection
from django_matrix.models import ProductRepresentation, ProductT9N
from django_matrix.repository.orm.prices import Prices as ProductPricesRepository
from django_matrix.services.attribute_service import fetch_and_attach_attributes
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import BundleQuery, get_view_variable_from_kwargs


def _get_stock_quantities(channel, sub_skus: list[str]) -> dict:
    """Returns {sku: saleable_quantity} from django_checkout Stock for the given SKUs.

    Uses Stock.annotated.saleable_quantity which already accounts for reservations,
    saleable_quantity_limit (buffer) and saleable_quantity_limit_per_order. Same
    source the fill_read_model_on_stock worker uses for matrix's denormalized stock.

    SKUs without a Stock record default to 0 (treat as out of stock). Empty dict when
    django_checkout is not available.
    """
    if not sub_skus:
        return {}

    # RuntimeError: an app that is installed but not in INSTALLED_APPS raises it on model import, not ImportError.
    try:
        from django_checkout.models import Stock
    except (ImportError, RuntimeError):
        return {}

    rows = Stock.annotated.filter(product__channel__idx=channel.idx, product__sku__in=sub_skus).values_list(
        "product__sku", "saleable_quantity"
    )

    return {sku: max(0, qty or 0) for sku, qty in rows}


def _get_simples_data(channel, language, sub_skus: list[str]) -> dict:
    """Returns {sku: {"name": str, "pictures": list[dict]}} for the given simple SKUs.

    Picture shape matches the listing endpoint's media-picture entries (Picture DTO).
    Falls back to base ProductRepresentation pictures when no T9N override exists.
    """
    if not sub_skus:
        return {}

    representations = ProductRepresentation.objects.filter(channel=channel, sku__in=sub_skus).prefetch_related(
        Prefetch(
            "t9ns",
            queryset=ProductT9N.objects.filter(language=language),
            to_attr="t9n_for_lang",
        )
    )

    result = {}
    for rep in representations:
        t9n = rep.t9n_for_lang[0] if rep.t9n_for_lang else None
        name = (t9n.name if t9n and t9n.name else None) or rep.sku
        pictures_raw = (t9n.pictures if t9n and t9n.pictures else None) or rep.pictures
        result[rep.sku] = {
            "name": name,
            "pictures": pictures_collection(pictures_raw, asdict=True),
        }
    return result


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(BundleQuery.Schema())
@prepare_view
def bundle_config_view(request, params: BundleQuery, *args, **kwargs) -> "Response":
    """Returns bundle structure: sub-items with flags, limits and prices"""

    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    customer = (
        request.user.customer if request.user is not None and getattr(request.user, "is_customer", False) else None
    )
    is_customer_verified = (
        customer.is_verified if customer is not None and hasattr(request.user.customer, "is_verified") else False
    )

    if not params.sku:
        raise NotFound("Bundle sku is required")

    bundle_skus = params.sku
    prices_repository = ProductPricesRepository(channel)
    bundle_links = get_bundle_subproducts(channel.idx, bundle_skus)
    bundle_limits = get_bundle_limits(channel.idx, bundle_skus)

    all_sub_skus = [sub_sku for meta in bundle_links.values() for sub_sku in meta.keys()]
    simples_data = _get_simples_data(channel, language, all_sub_skus)

    ranged_bundle_skus = {
        sku for sku, lim in bundle_limits.items() if lim.get("min") is not None or lim.get("max") is not None
    }
    ranged_sub_skus = [
        sub_sku
        for bundle_sku, meta in bundle_links.items()
        if bundle_sku in ranged_bundle_skus
        for sub_sku in meta.keys()
    ]
    stock_quantities = _get_stock_quantities(channel, ranged_sub_skus) if ranged_sub_skus else {}

    result = []
    for bundle_sku in bundle_skus:
        sub_items_meta = bundle_links.get(bundle_sku, {})
        limits = bundle_limits.get(bundle_sku, {})
        is_ranged = bundle_sku in ranged_bundle_skus

        prices_raw, msg = prices_repository.get_product_bundle_components_price(
            country_code=country.iso2,
            currency_code=currency.iso3,
            bundle_sku=bundle_sku,
            uid=None,
            is_customer_verified=is_customer_verified,
        )
        if msg:
            messages.append(msg)

        prices_by_sku, collection_msg = price_collection(
            prices_raw, asdict=True, channel=channel, country=country, currency=currency, customer=customer
        )
        if collection_msg:
            messages += collection_msg

        prices_map = {p["sku"]: p for p in prices_by_sku}

        # Ranged bundles ("pick N flavours"): is_default marks the reference set that defines the
        # listing price, not a selection to prefill. Preselecting it forces the customer to remove
        # 12 flavours before picking their own, so the configurator must start empty.
        sub_items = [
            {
                "sku": sub_sku,
                "name": simples_data.get(sub_sku, {}).get("name", sub_sku),
                "pictures": simples_data.get(sub_sku, {}).get("pictures", []),
                "quantity": None if is_ranged else meta["quantity"],
                "max_quantity": stock_quantities.get(sub_sku, 0) if is_ranged else None,
                "is_required": meta["is_required"],
                "is_default": False if is_ranged else meta["is_default"],
                "can_change_quantity": meta["can_change_quantity"],
                "price": prices_map.get(sub_sku),
            }
            for sub_sku, meta in sub_items_meta.items()
        ]

        result.append(
            {
                "sku": bundle_sku,
                "max_limit": limits.get("max"),
                "min_limit": limits.get("min"),
                "sub_items": sub_items,
            }
        )

    if params.fetch_attributes is True:
        all_sub_items = [si for bundle in result for si in bundle["sub_items"]]
        messages += fetch_and_attach_attributes(all_sub_items, channel=channel, language=language)

    return Response(result, messages=messages)
