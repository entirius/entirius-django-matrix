# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from _decimal import ROUND_UP, Decimal
from typing import TYPE_CHECKING

from process_logger import ProcessLoggerMixin

from django_matrix import settings
from django_matrix.models import Channel

if TYPE_CHECKING:
    from django_pricemanager.models import Price


class Prices(ProcessLoggerMixin):
    app_name: str = "django_pricemanager"
    CHUNK_SIZE: int = 10000
    channel: Channel

    def __init__(self, channel: Channel):
        self.channel = channel

    def set_channel(self, channel: Channel):
        self.channel = channel

    def calculate_badge(self, special_price, normal_price) -> Decimal:
        if special_price is not None and special_price > 0 and normal_price > 0:
            return round((100 - (special_price / normal_price * 100)), 0)
        else:
            return Decimal(0)

    def price_data(self, price_obj):
        sku = price_obj.product.sku
        # CurrentPrice has method is_eligible_for_special_price(); legacy Price has boolean field
        if hasattr(price_obj, "is_eligible_for_special_price") and callable(price_obj.is_eligible_for_special_price):
            is_egible_for_special_price = price_obj.is_eligible_for_special_price()
        else:
            is_egible_for_special_price = price_obj.is_egible_for_special_price
        tax_amount = (
            Decimal(price_obj.tax_rate.rate).quantize(Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP)
            if price_obj.tax_rate
            else None
        )
        tax_rule = str(round(price_obj.tax_rate.rate * 100)) + "%" if price_obj.tax_rate else None
        has_special_price = False
        if settings.PRICE_TYPE == "NET":
            final_price = (
                price_obj.special_net_value
                if price_obj.special_net_value and is_egible_for_special_price
                else price_obj.net_value
            )
            price_tax_config_opposite = price_obj.gross_value
            price = price_obj.net_value
            special_price = price_obj.special_net_value
            if special_price and is_egible_for_special_price:
                special_price = price_obj.special_net_value
                special_price_tax_config_opposite = special_price = Decimal(special_price).quantize(
                    Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP
                )
                has_special_price = True
            else:
                special_price = special_price_tax_config_opposite = None

        else:
            final_price = (
                price_obj.special_gross_value
                if price_obj.special_gross_value and is_egible_for_special_price
                else price_obj.gross_value
            )
            price = price_obj.gross_value
            price_tax_config_opposite = price_obj.net_value
            special_price = price_obj.special_gross_value
            if special_price and is_egible_for_special_price:
                special_price = Decimal(price_obj.special_gross_value).quantize(
                    Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP
                )
                special_price_tax_config_opposite = Decimal(price_obj.special_net_value).quantize(
                    Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP
                )
                has_special_price = True
            else:
                special_price = special_price_tax_config_opposite = None

        final_price = Decimal(final_price).quantize(Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP)
        price = Decimal(price).quantize(Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP)
        price_tax_config_opposite = Decimal(price_tax_config_opposite).quantize(
            Decimal(settings.PRICE_DECIMAL_PLACES), rounding=ROUND_UP
        )

        badge_value = self.calculate_badge(special_price, price)
        if badge_value > 0:
            promo_badge = str(badge_value) + "%"
        else:
            promo_badge = None

        special_from_date = price_obj.special_from_date
        special_to_date = price_obj.special_to_date

        return (
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
        )

    def price_as_dict(self, price_obj: Price, currency_code: str) -> dict:
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
        ) = self.price_data(price_obj)

        try:
            from django_omnibus.models import OmnibusPrice

            omnibus_query = OmnibusPrice.objects.filter(
                channel__idx=self.channel.idx, product__sku=sku, currency=currency_code
            ).first()
            omnibus_price = omnibus_query.omnibus_price if omnibus_query else None
        except ImportError:
            omnibus_price = None
        except Exception:
            import logging

            logging.getLogger("django_matrix").exception("Failed to fetch omnibus price for sku=%s", sku)
            omnibus_price = None

        return {
            "sku": sku,
            "is_range": False,
            "has_special_price": has_special_price,
            "price": price,
            "special_price": special_price,
            "tax_amount": tax_amount,
            "tax_rule": tax_rule,
            "promo_badge": promo_badge,
            "special_from_date": special_from_date,
            "special_to_date": special_to_date,
            "is_price_offer": False,
            "max_price_offer": None,
            "min_price_offer": None,
            "price_tax_config_opposite": price_tax_config_opposite,
            "special_price_tax_config_opposite": special_price_tax_config_opposite,
            "omnibus_price": omnibus_price,
        }

    def get_product_bundle_components_price(
        self,
        country_code: str,
        currency_code: str,
        bundle_sku: str,
        components_sku: list = None,
        uid: str | None = None,
        is_customer_verified: bool = False,
    ):
        try:
            from django_pricemanager.output_bundle import get_product_bundle_components_price
        except ImportError:
            return [], ""

        # Ceny składowe bundla nie obsługują cen przedziałowych (range price will always be null)
        prices, is_only_for_verified_user = get_product_bundle_components_price(
            self.channel.idx, country_code, currency_code, bundle_sku, components_sku, uid
        )
        if is_only_for_verified_user is True and is_customer_verified is False:
            return [], "Your are not verified customer and query may be limited"

        return [self.price_as_dict(price, currency_code) for price in prices], ""
