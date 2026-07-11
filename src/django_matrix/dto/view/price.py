# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django_accounts.models import Customer
from django_regional.models import Country, Currency

from django_matrix.dto import DTO
from django_matrix.models import Channel
from django_matrix.settings import (
    CACHE_TTL,
    LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX,
    USE_CACHED_VIEWS,
    USE_PRICE_TUNER_IN_MATRIX,
)

logger = logging.getLogger(__name__)


@dataclass
class Price(DTO):
    is_range: bool
    has_special_price: bool
    sku: str
    tax_amount: str
    tax_rule: str
    special_price: str
    special_price_range_from: str
    special_price_range_to: str
    promo_badge: str
    special_from_date: str
    special_to_date: str
    price: str
    range_from: str
    range_to: str
    is_price_offer: bool
    max_price_offer: str
    min_price_offer: str
    price_tax_config_opposite: str
    price_tax_config_opposite_from: str
    price_tax_config_opposite_to: str
    special_price_tax_config_opposite: str
    special_price_tax_config_opposite_from: str
    special_price_tax_config_opposite_to: str
    omnibus_price: str
    omnibus_price_from: str
    omnibus_price_to: str

    # You can build price view dto from db raw sql result
    def __init__(self, price: dict | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if price:
            self.sku = price["sku"] if "sku" in price else ""
            self.is_range = price["is_range"] if "is_range" in price else ""
            self.has_special_price = price["has_special_price"] if "has_special_price" in price else ""

            self.price = price["price"] if "price" in price else ""
            self.range_from = price["range_from"] if "range_from" in price else ""
            self.range_to = price["range_to"] if "range_to" in price else ""

            self.special_price = price["special_price"] if "special_price" in price else ""
            self.special_price_range_from = (
                price["special_price_range_from"] if "special_price_range_from" in price else ""
            )
            self.special_price_range_to = price["special_price_range_to"] if "special_price_range_to" in price else ""

            self.tax_amount = price["tax_amount"] if "tax_amount" in price else ""
            self.tax_rule = price["tax_rule"] if "tax_rule" in price else ""
            self.promo_badge = price["promo_badge"] if "promo_badge" in price else ""
            self.special_from_date = price["special_from_date"] if "special_from_date" in price else ""
            self.special_to_date = price["special_to_date"] if "special_to_date" in price else ""
            self.is_price_offer = price["is_price_offer"] if "is_price_offer" in price else False
            self.max_price_offer = price["max_price_offer"] if "max_price_offer" in price else ""
            self.min_price_offer = price["min_price_offer"] if "min_price_offer" in price else ""
            self.price_tax_config_opposite = (
                price["price_tax_config_opposite"] if "price_tax_config_opposite" in price else ""
            )
            self.price_tax_config_opposite_from = (
                price["price_tax_config_opposite_from"] if "price_tax_config_opposite_from" in price else ""
            )
            self.price_tax_config_opposite_to = (
                price["price_tax_config_opposite_to"] if "price_tax_config_opposite_to" in price else ""
            )

            self.special_price_tax_config_opposite = (
                price["special_price_tax_config_opposite"] if "special_price_tax_config_opposite" in price else ""
            )
            self.special_price_tax_config_opposite_from = (
                price["special_price_tax_config_opposite_from"]
                if "special_price_tax_config_opposite_from" in price
                else ""
            )
            self.special_price_tax_config_opposite_to = (
                price["special_price_tax_config_opposite_to"] if "special_price_tax_config_opposite_to" in price else ""
            )
            self.omnibus_price = price["omnibus_price"] if "omnibus_price" in price else ""
            self.omnibus_price_from = price["omnibus_price_from"] if "omnibus_price_from" in price else ""
            self.omnibus_price_to = price["omnibus_price_to"] if "omnibus_price_to" in price else ""

    def tune_price(self, channel: "Channel", country: "Country", currency: "Currency", customer: "Customer"):
        msg = []
        if not USE_PRICE_TUNER_IN_MATRIX:
            return msg

        if (
            "prices_listing" not in LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX
            or "prices_details" not in LIST_OF_DISABLED_CACHE_ENDPOINTS_MATRIX
            and USE_CACHED_VIEWS
            and type(CACHE_TTL) == int
        ):
            msg.append(
                "Caching is enabled for this endpoint, which may lead to distorted data with pricetuner by serving prices from a different group."
            )
        try:
            from django_pricetuner.output import PriceDTO, PriceTuner

            pt = PriceTuner(channel_idx=channel.idx)
            from django_accounts.models import Group

            user_group = customer.group if customer and customer.group else None
            pt.set_condition(group=user_group, price_country=country, price_currency=currency)

            prices = [
                PriceDTO(name="price", value=self.price),
                PriceDTO(name="range_from", value=self.range_from),
                PriceDTO(name="range_to", value=self.range_to),
                PriceDTO(name="price_tax_config_opposite", value=self.price_tax_config_opposite),
                PriceDTO(name="price_tax_config_opposite_from", value=self.price_tax_config_opposite_from),
                PriceDTO(name="price_tax_config_opposite_to", value=self.price_tax_config_opposite_to),
                PriceDTO(name="tax_amount", value=self.tax_amount, ignore_min_amount=True),
                PriceDTO(name="special_price", value=self.special_price),
                PriceDTO(name="special_price_range_from", value=self.special_price_range_from),
                PriceDTO(name="special_price_range_to", value=self.special_price_range_to),
                PriceDTO(name="special_price_tax_config_opposite", value=self.special_price_tax_config_opposite),
                PriceDTO(
                    name="special_price_tax_config_opposite_from", value=self.special_price_tax_config_opposite_from
                ),
                PriceDTO(name="special_price_tax_config_opposite_to", value=self.special_price_tax_config_opposite_to),
            ]

            prices = pt.tune_prices(prices, sku=self.sku)

        except ImportError:
            return msg
        except Exception as e:
            logger.exception(e)
            return msg
        else:
            # Saving only if above code didn't raise any exception
            for price_dto in prices:
                setattr(self, price_dto.name, price_dto.value)
        return msg


def price_collection(
    prices: dict,
    channel: "Channel",
    country: "Country",
    currency: "Currency",
    customer: "Customer",
    asdict: bool = False,
) -> tuple[list[Price], list[str]]:
    prices_col = []
    msg = []
    for price_dict in prices:
        price = Price(price=price_dict)

        # Use django_pricetuner
        msg = price.tune_price(channel=channel, country=country, currency=currency, customer=customer)

        if asdict:
            prices_col.append(price.asdict())
        else:
            prices_col.append(price)
    return prices_col, msg
