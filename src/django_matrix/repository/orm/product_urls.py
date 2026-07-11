# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_matrix.dto.view.product_url import ProductUrlsData
from django_matrix.dto.view.product_url_query import ProductUrlQuery
from django_matrix.models import Channel, ProductRepresentation, ProductT9N


class ProductUrlsRepository:
    def __init__(self, channel: Channel | None = None):
        self.channel = channel

    def get_product_representations(self, params: ProductUrlQuery) -> list[ProductRepresentation]:
        query = ProductRepresentation.objects.all()

        if params.sku:
            query = query.filter(sku__in=params.sku)
        elif params.url_key:
            query = self._filter_by_url_keys(query, params.url_key)

        if self.channel:
            query = query.filter(channel=self.channel)

        return query.select_related("channel")

    def _filter_by_url_keys(self, query, url_keys: list[str]):
        for url_key in url_keys:
            query_urls = query.filter(url_keys__contains=url_key)
            first_in_query = query_urls.first()
            if first_in_query:
                query = query.filter(sku=first_in_query.sku)
            else:
                query = query_urls
        return query

    def get_translations_by_product(self, product_ids: list[int]) -> dict[int, list[ProductT9N]]:
        translations = ProductT9N.objects.filter(product_representation_id__in=product_ids).select_related("language")

        translations_by_product = {}
        for t in translations:
            if t.product_representation_id not in translations_by_product:
                translations_by_product[t.product_representation_id] = []
            translations_by_product[t.product_representation_id].append(t)

        return translations_by_product

    def build_products_by_sku(
        self, product_representations: list[ProductRepresentation], translations_by_product: dict[int, list[ProductT9N]]
    ) -> dict[str, dict]:
        products_by_sku = {}

        for pr in product_representations:
            self._init_product_dict(products_by_sku, pr.sku)
            self._add_product_urls(products_by_sku, pr, translations_by_product)

        return products_by_sku

    def _init_product_dict(self, products_by_sku: dict, sku: str):
        if sku not in products_by_sku:
            products_by_sku[sku] = {"channels_url": {}}

    def _add_product_urls(
        self, products_by_sku: dict, pr: ProductRepresentation, translations_by_product: dict[int, list[ProductT9N]]
    ):
        channel_idx = pr.channel.idx
        urls_by_language = {}

        self._add_translations_urls(urls_by_language, pr.id, translations_by_product)
        self._add_url_keys_urls(urls_by_language, pr.url_keys)
        self._ensure_default_url(urls_by_language, pr)

        products_by_sku[pr.sku]["channels_url"][channel_idx] = urls_by_language

    def _add_translations_urls(
        self, urls_by_language: dict, product_id: int, translations_by_product: dict[int, list[ProductT9N]]
    ):
        if product_id in translations_by_product:
            for t in translations_by_product[product_id]:
                if t.url_key and t.language and t.language.iso2:
                    urls_by_language[t.language.iso2] = t.url_key

    def _add_url_keys_urls(self, urls_by_language: dict, url_keys):
        if url_keys:
            if isinstance(url_keys, dict):
                for lang_code, url_key in url_keys.items():
                    if isinstance(url_key, str):
                        urls_by_language[lang_code] = url_key
            elif isinstance(url_keys, list):
                for url_key in url_keys:
                    if isinstance(url_key, str) and "default" not in urls_by_language:
                        urls_by_language["default"] = url_key

    def _ensure_default_url(self, urls_by_language: dict, pr: ProductRepresentation):
        if "default" not in urls_by_language and urls_by_language:
            default_lang = pr.channel.default_language.iso2 if pr.channel.default_language else None
            if default_lang and default_lang in urls_by_language:
                urls_by_language["default"] = urls_by_language[default_lang]
            elif urls_by_language:
                first_lang = next(iter(urls_by_language))
                urls_by_language["default"] = urls_by_language[first_lang]

    def get_products_urls_data(self, params: ProductUrlQuery) -> list[dict]:
        product_representations = self.get_product_representations(params)

        product_ids = [pr.id for pr in product_representations]
        translations_by_product = self.get_translations_by_product(product_ids)

        products_by_sku = self.build_products_by_sku(product_representations, translations_by_product)

        return [ProductUrlsData(sku=sku, **data).asdict() for sku, data in products_by_sku.items()]
