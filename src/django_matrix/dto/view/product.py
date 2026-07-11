# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from django_matrix.dto import DTO
from django_matrix.dto.view.picture import Picture, pictures_collection
from django_matrix.dto.view.video import Video, videos_collection
from django_matrix.utils import convert_from_json

if TYPE_CHECKING:
    from django_accounts.models import Customer
    from django_regional.models import Country, Currency

    from django_matrix.models import Channel


@dataclass
class Product(DTO):
    sku: str
    product_type: str
    kind_of_product: str
    name: str
    url_key: str
    on_stock: bool
    have_product_links: bool | None = False
    final_price: str | None = None
    price_range: dict | None = None
    description: str | None = None
    short_description: str | None = None
    meta_description: str | None = None
    meta_title: str | None = None
    parent_sku: str | None = None
    parent_url_key: str | None = None
    badges: list[str] | None = None
    subnames: list[str] | None = None
    brands: list[str] | None = None
    media: list[Picture | Video] | None = None
    attributes: list | None = None
    average_rating: str | None = None
    number_of_reviews: str | None = None
    feature_set: dict | None = None
    children: list | None = None

    # You can build Product view dto from db raw sql result
    def __init__(self, product: dict | None = None, is_customer_verified: bool | None = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.badges = []
        self.subnames = []
        if product:
            is_only_for_verified_user = product["is_only_for_verified_user"] if "is_only_for_verified_user" else True
            show_price = not bool(not is_customer_verified and is_only_for_verified_user)
            self.sku = product["sku"] if "sku" in product else ""
            self.product_type = product["product_type"] if "product_type" in product else "BASE"
            self.name = product["name"] if "name" in product else self.sku
            self.description = product["desc"] if "desc" in product else ""
            self.short_description = product["short_desc"] if "short_desc" in product else ""
            self.url_key = product["url_key"] if "url_key" in product else ""
            self.on_stock = product["on_stock"] if "on_stock" in product else False
            self.have_product_links = product["have_product_links"] if "have_product_links" in product else False
            self.final_price = str(product["final_price"]) if "final_price" in product and show_price else None
            price_from = str(product["range_from"]) if "range_from" in product and show_price else None
            price_to = str(product["range_to"]) if "range_to" in product and show_price else None
            self.price_range = {"from": price_from, "to": price_to}
            self.parent_sku = product["parent_sku"] if "parent_sku" in product else None
            self.parent_url_key = product["parent_url_key"] if "parent_url_key" in product else None
            self.badges = convert_from_json(product["badges"]) if "badges" in product else None
            self.kind_of_product = product["kind_of_product"] if "kind_of_product" in product else "PHYSICAL"
            self.brands = convert_from_json(product["brands"]) if "brands" in product else None
            self.subnames = convert_from_json(product["subnames"]) if "subnames" in product else None
            self.meta_description = product["meta_description"] if "meta_description" in product else ""
            self.meta_title = product["meta_title"] if "meta_title" in product else ""
            self.average_rating = (
                str(product["average_rating"]) if "average_rating" in product and product["average_rating"] else None
            )
            self.number_of_reviews = (
                str(product["number_of_reviews"])
                if "number_of_reviews" in product and product["average_rating"]
                else None
            )
            pictures = pictures_collection(convert_from_json(product["pictures"])) if "pictures" in product else None
            videos = videos_collection(convert_from_json(product["videos"])) if "videos" in product else None
            self.media = pictures + videos if pictures and videos else pictures or videos
            if self.media:
                self.media = sorted(self.media, key=lambda x: x.position)
            self.attributes = []
            self.feature_set = convert_from_json(product["feature_set"]) if "feature_set" in product else None
            self.children = (
                convert_from_json(product["children"]) if "children" in product and product["children"] else []
            )


@dataclass
class ProductFullData(Product):
    """Extended Product DTO with full price data (used when fetch_full_data=true)"""

    stock_qty: int | None = None
    price: dict | None = None  # Nested Price object as dict

    def __init__(self, product: dict | None = None, is_customer_verified: bool | None = True, *args, **kwargs):
        super().__init__(product=product, is_customer_verified=is_customer_verified, *args, **kwargs)

        if product:
            self.stock_qty = product.get("stock_qty", 0)
            self.price = None


def product_collection(
    products: dict,
    asdict: bool = False,
    get_sku_list: bool = False,
    is_customer_verified: bool = True,
    include_full_price_data: bool = False,
    channel: Optional["Channel"] = None,
    country: Optional["Country"] = None,
    currency: Optional["Currency"] = None,
    customer: Optional["Customer"] = None,
) -> tuple[list[Product], list[str]] | tuple[list[Product], list[str], list[str]]:
    from django_matrix.dto.view.price import Price

    products_col = []
    sku_list = []
    messages = []
    product_class = ProductFullData if include_full_price_data else Product

    for product_dict in products:
        product = product_class(product=product_dict, is_customer_verified=is_customer_verified)
        sku_list.append(product.sku)

        if include_full_price_data and isinstance(product, ProductFullData):
            price_obj = Price(price=product_dict)
            if channel and country and currency:
                msg = price_obj.tune_price(channel=channel, country=country, currency=currency, customer=customer)
                if msg:
                    messages.extend(msg)
            product.price = price_obj.asdict()

        if asdict:
            products_col.append(product.asdict())
        else:
            products_col.append(product)

    if get_sku_list:
        if messages:
            return products_col, sku_list, messages
        return products_col, sku_list
    else:
        if messages:
            return products_col, messages
        return products_col
