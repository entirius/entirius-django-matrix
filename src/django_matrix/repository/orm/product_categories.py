# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.db.models import Q
from django_pim.models import Product, ProductCategory
from django_regional.models import Country, Currency, Language
from django_utils.api.exceptions import BadRequest, NotFound

from django_matrix.dto.view.category import Breadcrumb, Category
from django_matrix.models import Channel, ProductRepresentation
from django_matrix.settings import (
    BREADCRUMBS_WITHOUT_ROOT_CATEGORY_IN_VIEW,
    LIST_OF_BLACKLISTED_CATEGORIES_IDX_IN_VIEW,
)
from django_matrix.utils.params import ProductsCategoriesQuery


class ProductCategories:
    channel: Channel
    language: Language
    country: Country
    currency: Currency
    throw_api_view_errors_flag: bool

    language_iso2_cache: str = None

    def __init__(self, channel, language, country, currency):
        self.channel = channel
        self.language = language
        self.country = country
        self.currency = currency
        self.throw_api_view_errors_flag = False

    def throw_api_view_errors(self, flag: bool) -> "ProductCategories":
        self.throw_api_view_errors_flag = flag
        return self

    def get_language_iso(self):
        if not self.language_iso2_cache:
            self.language_iso2_cache = self.language.iso2.lower()
        return self.language_iso2_cache

    def find_by_api_query(self, params: ProductsCategoriesQuery):
        products = self.find_product_by_params(params)
        lang = self.get_language_iso()

        categories = []
        for product in products:
            product_categories = ProductCategory.objects.filter(
                product_in_category__product=product, is_active=True, is_in_menu=True
            ).exclude(idx__in=LIST_OF_BLACKLISTED_CATEGORIES_IDX_IN_VIEW)

            for pc in product_categories:
                breadcrumb_path = None
                breadcrumbs = None
                if params.breadcrumbs:
                    breadcrumb_path, breadcrumbs = self.build_breadcrumbs(
                        pc.get_breadcrumb_list(), separator=params.separator
                    )
                category = Category(
                    sku=product.sku,
                    idx=pc.idx,
                    name=pc.name_lang(lang),
                    url_key=pc.url_key_t9n[lang] if lang in pc.url_key_t9n else None,
                    tree_deep=pc.tree_deep,
                    position=pc.position,
                    external_id=pc.external_id,
                    breadcrumb_path=breadcrumb_path,
                    breadcrumbs=breadcrumbs,
                )
                categories.append(category)

        return categories

    def build_for_skus(self, skus: list[str], asdict: bool = True) -> dict:
        """Return {sku: [category dicts]} for the requested SKUs.

        Side-loading helper for the product views — swallows the "nothing matched" ValueError
        so an unknown SKU yields an empty mapping instead of failing the whole product response.
        """
        try:
            categories = self.find_by_api_query(ProductsCategoriesQuery(sku=skus))
        except ValueError:
            return {}

        result: dict[str, list] = {}
        for category in categories:
            result.setdefault(category.sku, []).append(category.asdict() if asdict else category)
        return result

    def build_breadcrumbs(self, categories: list[ProductCategory], separator: str = ">"):
        breadcrumb_path = []
        breadcrumbs = []
        lang = self.get_language_iso()
        for category in categories:
            if BREADCRUMBS_WITHOUT_ROOT_CATEGORY_IN_VIEW:
                if category.parent_category is None:
                    continue
            name = category.name_lang(lang)
            url_key = category.url_key_t9n[lang] if lang in category.url_key_t9n else None
            breadcrumb_path.append(name)
            breadcrumbs.append(Breadcrumb(name=name, url_key=url_key))

        return f" {separator} ".join(breadcrumb_path), breadcrumbs

    def find_product_by_params(self, params: ProductsCategoriesQuery):
        if params.url_key and len(params.url_key) > 0:
            return self.find_product_by_url_key(params.url_key)
        elif params.sku and len(params.sku) > 0:
            return self.find_product_by_sku(params.sku)
        else:
            if self.throw_api_view_errors_flag:
                raise BadRequest("Need url_key or sku in params")
            else:
                raise ValueError("Need url_key or sku in params")

    def find_product_by_sku(self, skus: list[str]):
        products = Product.objects.filter(shop__idx=self.channel.idx, real_product__sku__in=skus).prefetch_related(
            "real_product"
        )
        if products.exists():
            return products
        else:
            if self.throw_api_view_errors_flag:
                raise NotFound(f"Products for {skus} not found")
            else:
                raise ValueError(f"Products for {skus} not found")

    def find_product_by_url_key(self, url_keys: list[str]):
        q_objects = [Q(url_keys__contains=[url_key]) for url_key in url_keys]
        query = Q()
        for q in q_objects:
            query |= q

        products = ProductRepresentation.objects.filter(channel=self.channel).filter(query)
        if products.exists():
            skus = [product.sku for product in products]
            return self.find_product_by_sku(skus)
        else:
            if self.throw_api_view_errors_flag:
                raise NotFound(f"Products {url_keys} not found")
            else:
                raise ValueError(f"Products {url_keys} not found")
