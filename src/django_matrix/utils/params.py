# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import builtins
import json
import math
from collections import defaultdict
from dataclasses import asdict
from itertools import groupby
from typing import ClassVar

import marshmallow
from django_pim.models import Attribute
from magento2_sdk2.dto.search import SearchParameters
from marshmallow import Schema, fields, pre_load
from marshmallow_dataclass import dataclass

from django_matrix import settings
from django_matrix.enums import PaginationType


@dataclass
class SimpleQuery:
    """Query parameters contained in this dataclass, should be handled by all views"""

    currency: str | None = None
    language: str | None = None
    country: str | None = None

    Schema: ClassVar[type[Schema]] = Schema

    @pre_load
    def handle_parameter_list(self, data, **kwargs):
        """Aggregate values from list like parameters, for example from sku and sku[], into one field"""
        key_func = lambda x: x.strip("[]")
        grouped = groupby(sorted(data, key=key_func), key=key_func)
        result = {}
        for key, group in grouped:
            acc = []
            for elem in group:
                acc.extend(data.getlist(elem))

            field = self.declared_fields.get(key)
            if field is None:
                continue
            if isinstance(field, fields.List):
                result[key] = acc
            else:
                result[key] = acc[0]

        return result


@dataclass
class BaseQuery(SimpleQuery):
    """Query parameters contained in this dataclass, should be handled by all paginated views"""

    page: int | None = None
    limit: int | None = None
    # OFFSET stride. When a view inflates `limit` (e.g. page_size+1 to probe
    # has_next_page without a COUNT), set this to the real page size so
    # consecutive pages don't skip the extra probe row.
    page_size: int | None = None

    Schema: ClassVar[type[Schema]] = Schema

    def __post_init__(self):
        if self.page is None:
            self.page = 1
        if self.limit is None:
            self.limit = settings.PAGINATION_DEFAULT_RESULTS_COUNT
        if self.limit <= 0:
            self.limit = 1
        if self.limit > settings.PAGINATION_MAX_RESULTS_COUNT:
            self.limit = settings.PAGINATION_MAX_RESULTS_COUNT

    def offset(self):
        if self.page == 0 or self.page is None:
            self.page = 1
        stride = self.page_size if self.page_size else self.limit
        return (self.page - 1) * stride

    def pagination(self, count: int = 0, count_pages: int = 0) -> dict:
        pagination = {"page": self.page, "limit": self.limit}
        if settings.PAGINATION_TYPE == PaginationType.X_PAGES:
            pagination["pages"] = math.floor(count_pages / self.limit)
        if settings.PAGINATION_TYPE == PaginationType.FULL_PAGES:
            pagination["pages"] = math.ceil(count_pages / self.limit)
            pagination["count"] = count_pages
        pagination["results"] = count
        pagination["has_next_page"] = True if (self.limit - count) == 0 else False
        return pagination


@dataclass
class SelectFilter:
    feature_idx: str
    value_idx: list[str]

    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class Sorter:
    order: str
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class FeatureSorter(Sorter):
    feature_idx: str


@dataclass
class FieldSorter(Sorter):
    field: str


@dataclass
class PriceQuery(BaseQuery):
    sku: list[str] | None = None
    url_key: list[str] | None = None
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class BundleQuery(BaseQuery):
    sku: list[str] | None = None
    fetch_attributes: bool | None = None
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class Query(BaseQuery):
    sku: list[str] | None = None
    url_key: list[str] | None = None
    category_url_key: str | None = None
    query: list[dict] | None = None
    range: list[dict] | None = None
    search: list | None = None
    sort_feature: list[dict] | None = None
    sort: list[dict] | None = None
    type: str | None = None
    on_stock: bool | None = None
    has_special_price: bool | None = None
    magento_id: list[str] | None = None
    fetch_attributes: bool | None = None
    fetch_full_data: bool | None = None
    fetch_variant_groups: bool | None = None
    search_window: bool | None = None
    Schema: ClassVar[builtins.type[Schema]] = Schema

    @pre_load
    def handle_query(self, data, **kwargs):
        if "query" in data:
            result = {**data}
            result["query"] = [json.loads(elem) for elem in result.get("query")]
            return result
        return data

    @pre_load
    def handle_range(self, data, **kwargs):
        if "range" in data:
            result = {**data}
            result["range"] = [json.loads(elem) for elem in result.get("range")]
            return result
        return data

    @pre_load
    def handle_sort_feature(self, data, **kwargs):
        if "sort_feature" in data:
            result = {**data}
            result["sort_feature"] = [json.loads(elem) for elem in result.get("sort_feature")]
            return result
        return data

    @pre_load
    def handle_sort(self, data, **kwargs):
        if "sort" in data:
            result = {**data}
            result["sort"] = [json.loads(elem) for elem in result.get("sort")]
            return result
        return data


@dataclass
class DetailsQuery(SimpleQuery):
    fetch_attributes: bool | None = None
    fetch_variant_groups: bool | None = None
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class PriceDetailsQuery(SimpleQuery):
    Schema: ClassVar[type[Schema]] = Schema


def get_view_variable_from_kwargs(kwargs, require_channel=True) -> tuple:
    language = kwargs["language"] if "language" in kwargs else None
    currency = kwargs["currency"] if "currency" in kwargs else None
    country = kwargs["country"] if "country" in kwargs else None
    channel = kwargs["channel"] if "channel" in kwargs else None
    messages = kwargs["messages"] if "messages" in kwargs else []

    if channel is None and require_channel:
        raise ValueError("Channel is None inside view. Use prepare_view decorator.")

    return language, currency, country, channel, messages


def params_factory_for_details(params: DetailsQuery, **kwargs) -> Query:
    params_dict = asdict(params)
    query = Query(
        page=None,
        limit=None,
        sku=None,
        category_url_key=None,
        query=None,
        search=None,
        sort=None,
        type=None,
        on_stock=None,
        magento_id=None,
        **kwargs,
    )
    # got multiple values for keyword argument
    for key in params_dict.keys():
        if key in query.__dict__:
            query.__dict__[key] = params_dict[key]
    return query


def params_factory_for_price_details(params: PriceDetailsQuery, **kwargs) -> PriceQuery:
    params_dict = asdict(params)
    query = PriceQuery(page=None, limit=None, sku=None, **kwargs)
    # got multiple values for keyword argument
    for key in params_dict.keys():
        if key in query.__dict__:
            query.__dict__[key] = params_dict[key]
    return query


@dataclass
class MagentoQuery(Query, SearchParameters):
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class AttributeQuery(BaseQuery):
    sku: list[str] | None = None
    only_custom: bool | None = False
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class AttributeCustomQuery(BaseQuery):
    basic_sku: str = False
    query_custom: list[dict] | None = None
    Schema: ClassVar[type[Schema]] = Schema

    @pre_load
    def handle_query(self, data, **kwargs):
        if "query_custom" in data:
            result = {**data}
            result["query_custom"] = [json.loads(elem) for elem in result.get("query_custom")]
            return result
        return data

    @property
    def chosen_f9e_to_a9e(self):
        if self.query_custom:
            result = defaultdict(list)
            for lst in self.query_custom:
                for f9e, a9e in lst.items():
                    if isinstance(a9e, str):
                        a9e = [a9e]
                    if Attribute.objects.filter(idx__in=a9e, feature__idx=f9e).exists():
                        result[f9e].append(a9e)
            return result
        else:
            return {}


@dataclass
class AttributeCustomListingQuery(AttributeCustomQuery):
    only_chosen: bool | None = False


@dataclass
class VariantsQuery(SimpleQuery):
    url_key: str = ""
    on_stock: bool | None = None
    has_special_price: bool | None = None
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class OptionsQuery(Query):
    """Query parameters for options endpoint"""

    show_zeros: bool | None = False
    Schema: ClassVar[type[Schema]] = Schema

    @pre_load
    def handle_query(self, data, **kwargs):
        if "query" in data:
            result = {**data}
            result["query"] = [json.loads(elem) for elem in result.get("query")]
            return result
        return data


@dataclass
class CategoryListingQuery(SimpleQuery):
    depth: list[int] | None = None
    parent_url_key: str | None = None
    url_key: list[str] | None = None
    Schema: ClassVar[type[Schema]] = Schema

    class Meta:
        unknown = marshmallow.EXCLUDE

    @pre_load
    def handle_parameter_list(self, data, **kwargs):
        key_func = lambda x: x.strip("[]")
        grouped = groupby(sorted(data, key=key_func), key=key_func)
        result = {}
        for key, group in grouped:
            if key not in self.declared_fields:
                continue
            acc = []
            for elem in group:
                acc.extend(data.getlist(elem))
            field = self.declared_fields[key]
            if isinstance(field, fields.List):
                result[key] = acc
            else:
                result[key] = acc[0]
        return result


@dataclass
class ProductsCategoriesQuery(SimpleQuery):
    sku: list[str] | None = None
    url_key: list[str] | None = None
    separator: str = ">"
    breadcrumbs: bool = True
    Schema: ClassVar[type[Schema]] = Schema
