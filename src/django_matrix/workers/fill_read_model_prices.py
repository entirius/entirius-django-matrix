# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from decimal import Decimal

from process_logger import ProcessLogger

from django_matrix.enums import ProductType
from django_matrix.models import Channel, ProductPrice, ProductRepresentation
from django_matrix.repository.orm.prices import Prices
from django_matrix.utils.timestamp_print import timestamp_print

try:
    from django_pricemanager.output import (
        get_current_prices,
        get_latest_pricelist,
        get_price_qs_by_given_pricelist,
        read_from_current,
    )

    _HAS_PRICEMANAGER = True
except ImportError:
    _HAS_PRICEMANAGER = False
    read_from_current = lambda: False


def _set_v2_price_fields(
    ppp: "ProductPrice", price_obj, price_gross, price_net, special_gross, special_net, badge_value
):
    """Populate v2 explicit gross/net columns alongside v1 fields. Single pass, no extra queries."""
    ppp.gross = price_gross
    ppp.net = price_net
    ppp.final_gross = special_gross if special_gross else price_gross
    ppp.final_net = special_net if special_net else price_net
    ppp.special_gross = special_gross
    ppp.special_net = special_net
    ppp.percent_off = int(badge_value) if badge_value and badge_value > 0 else None


def _set_v2_range_fields(pp: "ProductPrice"):
    """Populate v2 net range fields from v1 opposite fields after parent range calculation."""
    if pp.is_range:
        pp.gross = None
        pp.net = None
        pp.final_gross = None
        pp.final_net = None
        pp.special_gross = None
        pp.special_net = None
        # range_from/to are gross (v1 convention when PRICE_TYPE=GROSS)
        # range_from_net/to_net from opposite fields
        pp.range_from_net = Decimal(pp.price_tax_config_opposite_from) if pp.price_tax_config_opposite_from else None
        pp.range_to_net = Decimal(pp.price_tax_config_opposite_to) if pp.price_tax_config_opposite_to else None
        pp.range_from_special_net = (
            Decimal(pp.special_price_tax_config_opposite_from) if pp.special_price_tax_config_opposite_from else None
        )
        pp.range_to_special_net = (
            Decimal(pp.special_price_tax_config_opposite_to) if pp.special_price_tax_config_opposite_to else None
        )
        pp.percent_off = (
            int(calculate_badge(pp.special_price_range_from, pp.range_from))
            if pp.special_price_range_from and pp.range_from
            else None
        )
    else:
        pp.gross = pp.range_from if pp.range_from else pp.gross
        pp.net = Decimal(pp.price_tax_config_opposite_from) if pp.price_tax_config_opposite_from else pp.net
        pp.final_gross = pp.special_price_range_from if pp.special_price_range_from else pp.gross
        pp.final_net = (
            Decimal(pp.special_price_tax_config_opposite_from) if pp.special_price_tax_config_opposite_from else pp.net
        )
        pp.special_gross = pp.special_price_range_from
        pp.special_net = (
            Decimal(pp.special_price_tax_config_opposite_from) if pp.special_price_tax_config_opposite_from else None
        )
        pp.range_from_net = None
        pp.range_to_net = None
        pp.range_from_special_net = None
        pp.range_to_special_net = None
        pp.percent_off = int(calculate_badge(pp.special_gross, pp.gross)) if pp.special_gross and pp.gross else None


def calculate_badge(special_price, normal_price) -> Decimal:
    if special_price is not None and special_price > 0 and normal_price > 0:
        return round((100 - (special_price / normal_price * 100)), 0)
    else:
        return Decimal(0)


def cache_omnibus_price(channel: Channel, product_id: str = None, logger: ProcessLogger = None) -> dict:
    try:
        from django_omnibus.models import OmnibusPrice
    except ImportError:
        if logger:
            logger.info("django_omnibus not available, skipping omnibus price cache")
        return {}

    timestamp_print("Cache omnibus prices")

    omnibus_query = (
        OmnibusPrice.objects.filter(channel__idx=channel.idx)
        .select_related("product")
        .only("omnibus_price", "currency", "product__sku")
    )

    if product_id:
        omnibus_query = omnibus_query.filter(product__sku=product_id)

    omnibus_cache = {}
    for price in omnibus_query:
        currency = price.currency
        sku = price.product.sku

        if currency not in omnibus_cache:
            omnibus_cache[currency] = {}

        omnibus_cache[currency][sku] = price.omnibus_price

    return omnibus_cache


_PP_UPDATE_FIELDS = [
    "is_range",
    "has_special_price",
    "price",
    "final_price",
    "promo_badge",
    "special_from_date",
    "special_to_date",
    "special_price",
    "special_price_range_from",
    "special_price_range_to",
    "tax_amount",
    "tax_rule",
    "price_tax_config_opposite",
    "special_price_tax_config_opposite",
    "price_tax_config_opposite_from",
    "price_tax_config_opposite_to",
    "special_price_tax_config_opposite_from",
    "special_price_tax_config_opposite_to",
    "is_only_for_verified_user",
    "min_price_offer",
    "max_price_offer",
    "is_price_offer",
    "omnibus_price",
    "omnibus_price_from",
    "omnibus_price_to",
    "range_from",
    "range_to",
    # v2 fields
    "gross",
    "net",
    "final_gross",
    "final_net",
    "special_gross",
    "special_net",
    "percent_off",
    "range_from_net",
    "range_to_net",
    "range_from_special_net",
    "range_to_special_net",
]


def _flush_price_batch(pp_modified: dict, process_logger: ProcessLogger) -> None:
    """Bulk-create new and bulk-update existing ProductPrice objects."""
    to_create = [pp for pp in pp_modified.values() if pp.pk is None]
    to_update = [pp for pp in pp_modified.values() if pp.pk is not None]

    if to_create:
        ProductPrice.objects.bulk_create(to_create, batch_size=500)
        process_logger.set_db_operation("CREATED", "django_matrix", "ProductPrice")
        process_logger.set_code(2010)
        process_logger.info(f"Bulk-created {len(to_create)} ProductPrice records.")
        process_logger.clear_db_operation()
    if to_update:
        ProductPrice.objects.bulk_update(to_update, fields=_PP_UPDATE_FIELDS, batch_size=500)
        process_logger.set_db_operation("UPDATE", "django_matrix", "ProductPrice")
        process_logger.set_code(2009)
        process_logger.info(f"Bulk-updated {len(to_update)} ProductPrice records.")
        process_logger.clear_db_operation()


def fill_read_model_prices(channel: Channel, product_id: str = None):
    if not _HAS_PRICEMANAGER:
        logging.getLogger("django_matrix").info("Skipping price fill: django_pricemanager not installed")
        return

    process_logger = ProcessLogger("FILL_READ_MODEL_PRICES")
    process_logger.add_log_param("channel_idx", channel.idx)

    prices_repository = Prices(channel)
    omnibus_cache = cache_omnibus_price(channel, product_id, process_logger)

    # Pre-fetch all ProductRepresentations for channel — avoids N+1 .get() per price
    pr_query = {"sku": product_id} if product_id else {}
    pr_cache = {
        pr.sku: pr for pr in ProductRepresentation.objects.filter(channel=channel, **pr_query).select_related("parent")
    }

    for country_obj in channel.countries.all():
        country = country_obj.iso2.upper()
        process_logger.add_log_param("country", country)
        for currency_obj in channel.currencies.all():
            currency = currency_obj.iso3.upper()
            process_logger.add_log_param("currency", currency)

            if read_from_current():
                prices = get_current_prices(channel.idx, currency, country, skus=[product_id] if product_id else None)
                if not prices.exists():
                    process_logger.warning(f"No CurrentPrices for channel {channel.idx}")
                    continue
                is_only_for_verified_user = prices.first().is_only_for_verified_user
            else:
                latest_pricelist = get_latest_pricelist(channel.idx, currency, country, None)
                if not latest_pricelist:
                    process_logger.warning(f"No pricelists for channel {channel.idx}")
                    continue
                prices = get_price_qs_by_given_pricelist(pricelist=latest_pricelist, sku=product_id)
                is_only_for_verified_user = latest_pricelist.sale_channel.is_only_for_verified_user

            # Pre-fetch all existing ProductPrice for this (channel, currency, country)
            pp_cache = {
                pp.product_representation_id: pp
                for pp in ProductPrice.objects.filter(
                    product_representation__channel=channel, currency=currency_obj, country=country_obj
                )
            }
            # Track all modified/created PPs — flushed at end of (country, currency) iteration
            pp_modified: dict[int, ProductPrice] = {}

            processed_parents_pk = []
            timestamp_print(f"[{country}][{currency}] prices: {len(prices)}")
            for price_obj in prices:
                try:
                    (
                        sku,
                        is_egible_for_special_price,
                        tax_amount,
                        tax_rule,
                        has_special_price,
                        final_price,
                        price,
                        price_tax_config_opposite,
                        special_price,
                        special_price_tax_config_opposite,
                        special_from_date,
                        special_to_date,
                        promo_badge,
                    ) = prices_repository.price_data(price_obj)

                    process_logger.add_log_param("product_sku", sku)

                    is_price_offer = False
                    max_price_offer = None
                    min_price_offer = None
                    try:
                        from django_checkout.output.sale_offer import get_offer_price_range

                        min_price_offer, max_price_offer = get_offer_price_range(sku, channel.idx, country, currency)
                        if min_price_offer and max_price_offer:
                            is_price_offer = True
                    except Exception as e:
                        process_logger.set_code(4025)
                        process_logger.exception(e)

                    omnibus_price = (
                        omnibus_cache[currency][sku]
                        if currency in omnibus_cache and sku in omnibus_cache[currency]
                        else None
                    )

                    pr = pr_cache.get(sku)
                    if not pr:
                        process_logger.set_code(2013)
                        process_logger.info(f"Price skipped. There is no sku: {sku} in ProductRepresentation")
                        process_logger.delete_log_param("product_sku")
                        continue

                    if pr.product_type in [ProductType.PRODUCT_SIMPLE, ProductType.PRODUCT_BUNDLE]:
                        try:
                            ppp = pp_cache.get(pr.pk)
                            if ppp is None:
                                ppp = ProductPrice(
                                    product_representation=pr,
                                    currency=currency_obj,
                                    country=country_obj,
                                    is_range=False,
                                    has_special_price=has_special_price,
                                    price=price,
                                    final_price=final_price,
                                    promo_badge=promo_badge,
                                    special_from_date=special_from_date,
                                    special_to_date=special_to_date,
                                    special_price=special_price,
                                    tax_amount=tax_amount,
                                    tax_rule=tax_rule,
                                    price_tax_config_opposite=price_tax_config_opposite,
                                    special_price_tax_config_opposite=special_price_tax_config_opposite,
                                    is_only_for_verified_user=is_only_for_verified_user,
                                    min_price_offer=min_price_offer,
                                    max_price_offer=max_price_offer,
                                    is_price_offer=is_price_offer,
                                    omnibus_price=omnibus_price,
                                )
                                _set_v2_price_fields(
                                    ppp,
                                    price_obj,
                                    price_obj.gross_value,
                                    price_obj.net_value,
                                    price_obj.special_gross_value if has_special_price else None,
                                    price_obj.special_net_value if has_special_price else None,
                                    calculate_badge(special_price, price),
                                )
                                pp_cache[pr.pk] = ppp
                            else:
                                ppp.is_range = False
                                ppp.has_special_price = has_special_price
                                ppp.price = price
                                ppp.final_price = final_price
                                ppp.promo_badge = promo_badge
                                ppp.special_from_date = special_from_date
                                ppp.special_to_date = special_to_date
                                ppp.special_price = special_price
                                ppp.tax_amount = tax_amount
                                ppp.tax_rule = tax_rule
                                ppp.price_tax_config_opposite = price_tax_config_opposite
                                ppp.special_price_tax_config_opposite = special_price_tax_config_opposite
                                ppp.is_only_for_verified_user = is_only_for_verified_user
                                ppp.min_price_offer = min_price_offer
                                ppp.max_price_offer = max_price_offer
                                ppp.is_price_offer = is_price_offer
                                ppp.omnibus_price = omnibus_price
                                _set_v2_price_fields(
                                    ppp,
                                    price_obj,
                                    price_obj.gross_value,
                                    price_obj.net_value,
                                    price_obj.special_gross_value if has_special_price else None,
                                    price_obj.special_net_value if has_special_price else None,
                                    calculate_badge(special_price, price),
                                )
                            pp_modified[id(ppp)] = ppp
                        except Exception as e:
                            process_logger.set_code(4009)
                            process_logger.exception(e)

                        if pr.parent:
                            parent = pr.parent
                            try:
                                pp = pp_cache.get(parent.pk)
                                if pp is None:
                                    pp = ProductPrice(
                                        product_representation=parent,
                                        currency=currency_obj,
                                        country=country_obj,
                                        is_range=False,
                                        price=price,
                                        final_price=final_price,
                                        special_price=special_price,
                                        has_special_price=has_special_price,
                                        tax_rule=tax_rule,
                                        tax_amount=tax_amount,
                                        promo_badge=promo_badge,
                                        special_from_date=special_from_date,
                                        special_to_date=special_to_date,
                                        price_tax_config_opposite=price_tax_config_opposite,
                                        special_price_tax_config_opposite=special_price_tax_config_opposite,
                                        is_only_for_verified_user=is_only_for_verified_user,
                                        omnibus_price=omnibus_price,
                                    )
                                    _set_v2_price_fields(
                                        pp,
                                        price_obj,
                                        price_obj.gross_value,
                                        price_obj.net_value,
                                        price_obj.special_gross_value if has_special_price else None,
                                        price_obj.special_net_value if has_special_price else None,
                                        calculate_badge(special_price, price),
                                    )
                                    pp_cache[parent.pk] = pp
                                    processed_parents_pk.append(parent.pk)
                                else:
                                    # Wymuś aktualizację zakresu cen dla rodzica, i nie odnoś się do starej danych parenta przy pierwszej iteracji dla danego rodzica
                                    first_iteration_for_parent = parent.pk not in processed_parents_pk

                                    # Jeśli pola zakresu były wyczyszczone (stan bez zakresu), przywróć je z pól pojedynczej ceny do trackowania
                                    if pp.range_from is None and not first_iteration_for_parent:
                                        pp.range_from = pp.price
                                        pp.range_to = pp.price
                                        pp.price_tax_config_opposite_from = pp.price_tax_config_opposite
                                        pp.price_tax_config_opposite_to = pp.price_tax_config_opposite
                                        if pp.special_price is not None:
                                            pp.special_price_range_from = pp.special_price
                                            pp.special_price_range_to = pp.special_price
                                        if pp.special_price_tax_config_opposite is not None:
                                            pp.special_price_tax_config_opposite_from = (
                                                pp.special_price_tax_config_opposite
                                            )
                                            pp.special_price_tax_config_opposite_to = (
                                                pp.special_price_tax_config_opposite
                                            )
                                        if pp.omnibus_price is not None:
                                            pp.omnibus_price_from = pp.omnibus_price
                                            pp.omnibus_price_to = pp.omnibus_price

                                    if pp.range_from is None or first_iteration_for_parent or price < pp.range_from:
                                        pp.range_from = price
                                    if pp.range_to is None or first_iteration_for_parent or price > pp.range_to:
                                        pp.range_to = price

                                    if (
                                        pp.price_tax_config_opposite_from is None
                                        or first_iteration_for_parent
                                        or price_tax_config_opposite < Decimal(pp.price_tax_config_opposite_from)
                                    ):
                                        pp.price_tax_config_opposite_from = price_tax_config_opposite
                                    if (
                                        pp.price_tax_config_opposite_to is None
                                        or first_iteration_for_parent
                                        or price_tax_config_opposite > Decimal(pp.price_tax_config_opposite_to)
                                    ):
                                        pp.price_tax_config_opposite_to = price_tax_config_opposite

                                    if special_price:
                                        if (
                                            pp.special_price_range_from is None
                                            or first_iteration_for_parent
                                            or special_price < pp.special_price_range_from
                                        ):
                                            pp.special_price_range_from = special_price
                                        if (
                                            pp.special_price_range_to is None
                                            or first_iteration_for_parent
                                            or special_price > pp.special_price_range_to
                                        ):
                                            pp.special_price_range_to = special_price

                                        if (
                                            pp.special_price_tax_config_opposite_from is None
                                            or first_iteration_for_parent
                                            or (
                                                special_price_tax_config_opposite is not None
                                                and pp.special_price_tax_config_opposite_from is not None
                                                and special_price_tax_config_opposite
                                                < Decimal(pp.special_price_tax_config_opposite_from)
                                            )
                                        ):
                                            pp.special_price_tax_config_opposite_from = (
                                                special_price_tax_config_opposite
                                            )
                                        if (
                                            pp.special_price_tax_config_opposite_to is None
                                            or first_iteration_for_parent
                                            or (
                                                special_price_tax_config_opposite is not None
                                                and pp.special_price_tax_config_opposite_to is not None
                                                and special_price_tax_config_opposite
                                                > Decimal(pp.special_price_tax_config_opposite_to)
                                            )
                                        ):
                                            pp.special_price_tax_config_opposite_to = special_price_tax_config_opposite

                                        badge_value = calculate_badge(pp.special_price_range_from, pp.range_from)
                                        if badge_value > 0:
                                            pp.promo_badge = str(badge_value) + "%"
                                        else:
                                            pp.promo_badge = None

                                    if omnibus_price:
                                        if (
                                            pp.omnibus_price_from is None
                                            or first_iteration_for_parent
                                            or omnibus_price < pp.omnibus_price_from
                                        ):
                                            pp.omnibus_price_from = omnibus_price
                                        if (
                                            pp.omnibus_price_to is None
                                            or first_iteration_for_parent
                                            or omnibus_price > pp.omnibus_price_to
                                        ):
                                            pp.omnibus_price_to = omnibus_price

                                    pp.is_range = pp.range_from != pp.range_to
                                    if pp.is_range:
                                        pp.price = None
                                        pp.final_price = None
                                        pp.special_price = None
                                        pp.price_tax_config_opposite = None
                                        pp.special_price_tax_config_opposite = None
                                        pp.omnibus_price = None
                                    else:
                                        pp.price = pp.range_from
                                        pp.final_price = (
                                            pp.special_price_range_from
                                            if pp.special_price_range_from
                                            else pp.range_from
                                        )
                                        pp.special_price = pp.special_price_range_from
                                        pp.price_tax_config_opposite = pp.price_tax_config_opposite_from
                                        pp.special_price_tax_config_opposite = pp.special_price_tax_config_opposite_from
                                        pp.omnibus_price = pp.omnibus_price_from
                                        pp.range_from = None
                                        pp.range_to = None
                                        pp.special_price_range_from = None
                                        pp.special_price_range_to = None
                                        pp.price_tax_config_opposite_from = None
                                        pp.price_tax_config_opposite_to = None
                                        pp.special_price_tax_config_opposite_from = None
                                        pp.special_price_tax_config_opposite_to = None
                                        pp.omnibus_price_from = None
                                        pp.omnibus_price_to = None
                                    pp.has_special_price = has_special_price
                                    pp.special_from_date = special_from_date
                                    pp.special_to_date = special_to_date
                                    pp.tax_amount = tax_amount
                                    pp.tax_rule = tax_rule
                                    pp.is_only_for_verified_user = is_only_for_verified_user
                                    # v2 dual-write: set range net fields from v1 opposite fields
                                    _set_v2_range_fields(pp)
                                    processed_parents_pk.append(parent.pk)
                                pp_modified[id(pp)] = pp
                            except Exception as e:
                                process_logger.set_code(4011)
                                process_logger.exception(e)

                    process_logger.add_log_param("product_sku", sku)
                except Exception as e:
                    process_logger.set_code(4024)
                    process_logger.exception(e)

            # Flush all modified/created prices for this (country, currency)
            _flush_price_batch(pp_modified, process_logger)
            process_logger.delete_log_param("currency")

        process_logger.delete_log_param("country")
