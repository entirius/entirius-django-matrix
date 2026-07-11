# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_pim.models import ProductCategory

from django_matrix.dto.view.category_url import CategoryUrlsData
from django_matrix.dto.view.category_url_query import CategoryUrlQuery
from django_matrix.models import Channel


class CategoryUrlsRepository:
    def __init__(self, channel: Channel | None = None):
        self.channel = channel

    def get_categories(self, params: CategoryUrlQuery) -> list[ProductCategory]:
        query = ProductCategory.objects.filter(is_active=True)
        if params.idx:
            query = query.filter(idx__in=params.idx)
        elif params.url_key:
            query = self._filter_by_url_keys(query, params.url_key)
        if self.channel:
            query = query.filter(shop__idx=self.channel.idx)
        return query.select_related("shop")

    def _filter_by_url_keys(self, query, url_keys: list[str]):
        for url_key in url_keys:
            # sql injection safety
            query_urls = query.extra(
                where=["EXISTS (SELECT 1 FROM jsonb_each_text(url_key_t9n::jsonb) WHERE value = %s)"], params=[url_key]
            )

            first_in_query = query_urls.first()
            if first_in_query:
                query = query.filter(idx=first_in_query.idx)
            else:
                query = query_urls
        return query

    def build_categories(self, categories: list[ProductCategory]) -> dict[str, dict]:
        categories_by_sku = {}
        for category in categories:
            category_url_key_t9n = category.url_key_t9n
            category_url_key_t9n = self._ensure_default_url(category_url_key_t9n, category.shop)
            if str(category.idx) not in categories_by_sku:
                categories_by_sku[str(category.idx)] = {
                    "channels_url": {},
                }
            category_url_key_t9n = {k: v for k, v in category_url_key_t9n.items() if v}
            categories_by_sku[str(category.idx)]["channels_url"][category.shop.idx] = category_url_key_t9n
        return categories_by_sku

    @staticmethod
    def _ensure_default_url(category_url_key_t9n, shop):
        if "default" not in category_url_key_t9n and category_url_key_t9n:
            default_lang = shop.default_language.iso2 if shop.default_language else None
            if default_lang and default_lang in category_url_key_t9n:
                category_url_key_t9n["default"] = category_url_key_t9n[default_lang]
            elif category_url_key_t9n:
                first_lang = next(iter(category_url_key_t9n))
                category_url_key_t9n["default"] = category_url_key_t9n[first_lang]
        return category_url_key_t9n

    def get_categories_urls_data(self, params: CategoryUrlQuery) -> list[dict]:
        categories = self.get_categories(params)

        categories_by_sku = self.build_categories(categories)

        return [CategoryUrlsData(idx=idx, **data).asdict() for idx, data in categories_by_sku.items()]
