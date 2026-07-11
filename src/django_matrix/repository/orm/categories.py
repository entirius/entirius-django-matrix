# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Count, Exists, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django_pim.models import ProductCategory, ProductInCategory

from django_matrix.dto.view.category import Category
from django_matrix.models import Channel
from django_matrix.utils.params import CategoryListingQuery


class CategoriesRepository:
    def __init__(self, channel: Channel):
        self.channel = channel

    def get_categories(self, params: CategoryListingQuery, language_iso2: str) -> list[dict]:
        qs = ProductCategory.objects.filter(
            shop__idx=self.channel.idx,
            is_in_menu=True,
            is_active=True,
        )
        if params.depth:
            qs = qs.filter(tree_deep__in=params.depth)
        if params.url_key:
            qs = self._filter_by_url_keys(qs, params.url_key, language_iso2)
        if params.parent_url_key:
            qs = self._filter_by_parent_url_key(qs, params.parent_url_key, language_iso2)

        products_count_subquery = Coalesce(
            Subquery(
                ProductInCategory.objects.filter(category_id=OuterRef("pk"))
                .values("category_id")
                .annotate(count=Count("product_id"))
                .values("count")[:1],
                output_field=IntegerField(),
            ),
            0,
        )

        data = (
            qs.annotate(
                has_children=Exists(ProductCategory.objects.filter(parent_category=OuterRef("pk"))),
                products_count=products_count_subquery,
            )
            .order_by("position")
            .values(
                "idx",
                "parent_category__idx",
                "position",
                "tree_deep",
                "rich_content",
                "external_id",
                f"name_t9n__{language_iso2}",
                f"url_key_t9n__{language_iso2}",
                f"description_t9n__{language_iso2}",
                f"meta_title_t9n__{language_iso2}",
                f"meta_description_t9n__{language_iso2}",
                "has_children",
                "products_count",
            )
        )

        return self._format(data, language_iso2)

    def _format(self, data, language_iso2: str) -> list[dict]:
        result = []
        for elem in data:
            category = Category(
                idx=elem["idx"],
                name=elem[f"name_t9n__{language_iso2}"],
                url_key=elem[f"url_key_t9n__{language_iso2}"],
                tree_deep=elem["tree_deep"],
                position=elem["position"],
                has_children=elem["has_children"],
                products_count=elem["products_count"],
                parent_idx=elem["parent_category__idx"],
                external_id=elem["external_id"],
                meta_title=elem[f"meta_title_t9n__{language_iso2}"],
                meta_description=elem[f"meta_description_t9n__{language_iso2}"],
                description=elem[f"description_t9n__{language_iso2}"],
                rich_content=elem["rich_content"],
            )
            result.append(category.asdict())
        return result

    def _filter_by_url_keys(self, qs, url_keys: list[str], language_iso2: str):
        placeholders = ", ".join(["%s"] * len(url_keys))
        return qs.extra(
            where=[f"EXISTS (SELECT 1 FROM jsonb_each_text(url_key_t9n::jsonb) WHERE value IN ({placeholders}))"],
            params=url_keys,
        )

    def _filter_by_parent_url_key(self, qs, parent_url_key: str, language_iso2: str):
        parent = (
            ProductCategory.objects.filter(
                shop__idx=self.channel.idx,
            )
            .extra(
                where=["EXISTS (SELECT 1 FROM jsonb_each_text(url_key_t9n::jsonb) WHERE value = %s)"],
                params=[parent_url_key],
            )
            .first()
        )
        if parent:
            qs = qs.filter(parent_category=parent)
        else:
            qs = qs.none()
        return qs
