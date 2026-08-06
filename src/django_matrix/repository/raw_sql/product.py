# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from django_regional.models import Country, Currency, Language

from django_matrix import settings
from django_matrix.enums import FeatureType, Filtering, PaginationType, ProductType, Sorting
from django_matrix.models import Channel
from django_matrix.repository.django_pim import get_feature, get_feature_type
from django_matrix.repository.raw_sql import DbConnect
from django_matrix.repository.raw_sql.warning_codes import WarningCode
from django_matrix.settings import (
    MATRIX_FULL_TEXT_LANG_SEARCH,
    MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT,
    MATRIX_PRODUCTS_PARALLEL_QUERIES,
    MATRIX_SEARCH_DEFAULT_SORT,
)
from django_matrix.utils.params import Query
from django_matrix.utils.unit_options import to_canonical


class Product(DbConnect):
    app_name = "django_matrix"
    product_table_name = "productrepresentation"
    t9n_table_name = "productt9n"
    price_table_name = "productprice"
    attribute_table_name = "attribute"
    sep = ","

    @staticmethod
    def get_all_system_sort():
        return [Sorting.SKU, Sorting.NAME, Sorting.CREATED, Sorting.PRICE, Sorting.ON_STOCK, Sorting.RELEVANCE]

    def _warn(self, code: str, param: str, message: str) -> None:
        """Record a non-blocking, user-facing warning for an ignored q_/r_/s_ param."""
        if not hasattr(self, "_warnings"):
            self._warnings = []
        self._warnings.append({"code": code, "param": param, "message": message})

    def get_order_type(self, channel: Channel, order_type, orders, direction, messages=None, param=None):
        if messages is None:
            messages = []

        match order_type:
            case Sorting.SKU:
                if channel.sku_order_numeric_sort:
                    orders.append(
                        f"CASE WHEN pr.sku ~ '^[0-9]+$' THEN pr.sku::integer ELSE NULL END {direction} NULLS LAST "
                    )
                orders.append(f"pr.sku {direction} ")
            case Sorting.NAME:
                orders.append(f"pt.name {direction} ")
            case Sorting.CREATED:
                orders.append(f"pr.created_at {direction} ")
            case Sorting.PRICE:
                orders.append(f"COALESCE(pp.final_price, pp.range_from) {direction} ")
                # stable sort - te same endpointy zwrócą te same wyniki w przypadku tej samej ceny
                orders.append("pr.id ASC ")
            case Sorting.ON_STOCK:
                orders.append(f"pr.on_stock {direction} ")
            case Sorting.RELEVANCE:
                if hasattr(self, "_has_search_ranking") and self._has_search_ranking:
                    orders.append(f"search_rank {direction} ")
                else:
                    # Internal default sort for /search/ — not a user-facing q_/r_/s_ param, log only.
                    messages.append("Relevance sorting is only available when searching with full-text search enabled")
            case _:
                msg = f"field {order_type} can't be sorted by"
                messages.append(msg)
                if param:
                    self._warn(WarningCode.SORT_UNKNOWN_FIELD, param, msg)
        return orders, messages

    def _apply_search_default_sort(self, orders, channel, restrictions, sql_params, counter, messages):
        if not MATRIX_SEARCH_DEFAULT_SORT:
            return orders, messages, counter

        sortable_idx_set = set(restrictions.get("sortable", []))
        sortable_idx_set.update(
            channel.sortable_features.all().prefetch_related("feature").values_list("feature__idx", flat=True)
        )

        for field, direction in MATRIX_SEARCH_DEFAULT_SORT.items():
            direction = self.get_asc_desc(direction)

            if field in self.get_all_system_sort():
                orders, messages = self.get_order_type(channel, field, orders, direction, messages)
            else:
                if field not in sortable_idx_set:
                    messages.append(f"MATRIX_SEARCH_DEFAULT_SORT: feature_idx {field} is not sortable in channel")
                    continue

                feature_type = get_feature_type(field)
                param_f = f"sort_{counter}"
                sql_params[param_f] = field

                if feature_type == FeatureType.DATETIME:
                    orders.append(f"(pr.attributes_filter ->> %({param_f})s)::timestamp {direction} NULLS LAST ")
                elif feature_type in [
                    FeatureType.SELECT,
                    FeatureType.MULTISELECT,
                    FeatureType.TEXT,
                    FeatureType.DECIMAL,
                ]:
                    orders.append(f"pr.attributes_filter -> %({param_f})s {direction} NULLS LAST ")

            counter += 1

        return orders, messages, counter

    def find_by_api_query(
        self,
        params: Query,
        channel: "Channel",
        language: "Language",
        country: "Country",
        currency: "Currency",
        is_customer_verified: bool,
        apply_default_order: bool = True,
        limit_offset: bool = True,
        skip_or_filterable_features=False,
        only_generate_sql=False,
        only_generate_minimal_sql=False,
        custom_sort=None,
        sku_subquery: tuple[str, dict] | None = None,
    ):
        def split_list(values: list, param_name: str, additional_counter: int | None = None):
            i = 1
            result = []
            for val in values:
                if additional_counter:
                    param = f"{param_name}_{additional_counter}_{i}"
                else:
                    param = f"{param_name}_{i}"
                # This is adding to shadow variable sql_params so keep this method here or return it and add to sql_params
                sql_params[param] = val
                result.append(f"%({param})s")
                i += 1
            return result

        messages = []
        self._warnings = []

        self._has_search_ranking = False

        # Get restrictions
        restrictions = channel.get_featuers_restrictions(params=params)

        sql_params = {"channel_id": channel.pk}

        sku_subquery_join = ""
        if sku_subquery:
            sku_subquery_join = f"INNER JOIN ({sku_subquery[0]}) AS sku_filter ON pr.sku = sku_filter.sku "
            sql_params.update(sku_subquery[1])

        search_rank_select = ""

        if params.search and settings.MATRIX_FULL_TEXT_SEARCH:
            self._has_search_ranking = True
            lang_tsvector = self.prepare_weighted_tsvector(MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT, language)
            simple_tsvector = self.prepare_weighted_tsvector(MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT)

            search_rank_select = f", ts_rank({lang_tsvector}, to_tsquery('{self.get_full_text_search_lang(language)}', %(ts_search_str)s)) + ts_rank({simple_tsvector}, to_tsquery('simple', %(ts_search_str)s)) AS search_rank "

        sql = (
            f"SELECT pr.id, pr.sku, pr.product_type, pr.on_stock, pr.stock_qty, ppr.sku as parent_sku, pr.feature_set, pr.have_product_links, pr.kind_of_product, pr.average_rating, pr.number_of_reviews, pr.children, "
            f"pt.name, pt.desc, pt.short_desc, pt.url_key, pt.badges, pt.brands, pt.subnames, pt.meta_title, pt.meta_description, "
            f"COALESCE(pt.pictures, pr.pictures) AS pictures, "
            f"COALESCE(pt.videos, pr.videos) AS videos, "
            f"ppt.url_key as parent_url_key, "
            # Podstawowe ceny i zakresy
            f"pp.final_price, pp.price, pp.range_from, pp.range_to, pp.is_range, "
            f"pp.gross, pp.net, pp.final_gross, pp.final_net, "
            # Promocje i Special Prices
            f"pp.has_special_price, pp.special_price, pp.percent_off, pp.promo_badge, "
            f"pp.special_from_date, pp.special_to_date, "
            f"pp.special_gross, pp.special_net, "
            f"pp.special_price_range_from, pp.special_price_range_to, "
            # Netto/Brutto dla zakresów
            f"pp.range_from_net, pp.range_to_net, "
            f"pp.range_from_special_net, pp.range_to_special_net, "
            # Omnibus i Podatki
            f"pp.omnibus_price, pp.omnibus_price_from, pp.omnibus_price_to, "
            f"pp.tax_amount, pp.tax_rule, "
            # Konfiguracje Tax Opposite
            f"pp.price_tax_config_opposite, pp.price_tax_config_opposite_from, pp.price_tax_config_opposite_to, "
            f"pp.special_price_tax_config_opposite, pp.special_price_tax_config_opposite_from, pp.special_price_tax_config_opposite_to, "
            # Oferty i Uprawnienia
            f"pp.is_price_offer, pp.min_price_offer, pp.max_price_offer, "
            f"pp.is_only_for_verified_user, "
            # Dane produktu (prefix pr.)
            f"pr.is_virtual, pr.main_image, pr.categories_data, pr.attachments, pr.product_links "
            f"{search_rank_select}"
            f"FROM {self.app_name}_{self.product_table_name} AS pr "
            f"{sku_subquery_join}"
            f"LEFT JOIN {self.app_name}_{self.product_table_name} AS ppr "
            f"ON pr.parent_id = ppr.id "
            f"LEFT JOIN {self.app_name}_{self.t9n_table_name} AS pt "
            f"ON pr.id = pt.product_representation_id AND pt.language_id = {language.pk} "
            f"LEFT JOIN {self.app_name}_{self.t9n_table_name} AS ppt "
            f"ON ppr.id = ppt.product_representation_id AND ppt.language_id = {language.pk} "
            f"LEFT JOIN {self.app_name}_{self.price_table_name} AS pp "
            f"ON pr.id = pp.product_representation_id AND pp.currency_id = {currency.pk} AND pp.country_id = {country.pk} "
            f"WHERE pr.channel_id = %(channel_id)s "
        )

        # Filter by type
        if params.type and params.type != "ALL":
            if params.type in [
                ProductType.PRODUCT_SIMPLE,
                ProductType.PRODUCT_CONFIGURABLE,
                ProductType.PRODUCT_BASE,
                ProductType.PRODUCT_BUNDLE,
                ProductType.PRODUCT_CUSTOM,
            ]:
                sql_params["type"] = params.type
                sql += "AND pr.product_type = %(type)s "
            elif params.type == "ORPHAN":
                sql_params["type_s"] = ProductType.PRODUCT_SIMPLE
                sql_params["type_c"] = ProductType.PRODUCT_CONFIGURABLE
                sql += "AND (pr.product_type = %(type_c)s OR (pr.product_type = %(type_s)s AND pr.parent_id IS NULL)) "

        # Filter by on_stock
        if params.on_stock is not None:
            sql += "AND pr.on_stock = %(on_stock)s "
            sql_params["on_stock"] = params.on_stock

        if params.has_special_price is not None:
            # pp is LEFT JOINed: a product without a price row for this currency/country
            # yields NULL, and `NULL = false` is NULL — which would silently drop it from
            # a `has_special_price=false` listing. No price row means no special price.
            sql += "AND COALESCE(pp.has_special_price, FALSE) = %(has_special_price)s "
            sql_params["has_special_price"] = params.has_special_price
            if params.has_special_price:
                sql += "AND (pp.special_from_date IS NULL OR pp.special_from_date::timestamp <= NOW()) "
                sql += "AND (pp.special_to_date IS NULL OR pp.special_to_date::timestamp >= NOW()) "

        # Filter by magento_id
        if params.magento_id:
            sql += "AND pr.magento_id IN %(magento_id)s "
            sql_params["magento_id"] = tuple(params.magento_id)

        # Find by SKU
        if params.sku:
            skus = split_list(params.sku, "sku")
            sql += f"AND pr.sku IN ({self.sep.join(skus)}) "

        # Find by Product URL KEY
        if params.url_key:
            if len(params.url_key) > 1:
                url_keys = split_list(params.url_key, "url_key")
                sql += f"AND pr.url_keys ?| array[{self.sep.join(url_keys)}] "
            elif len(params.url_key) == 1:
                sql += "AND pr.url_keys ? %(url_key)s "
                sql_params["url_key"] = params.url_key[0]

        # Find by Categories URL KEY
        if params.category_url_key:
            sql += "AND pr.categories_url_key ? %(cat_url_key)s "
            sql_params["cat_url_key"] = params.category_url_key

        # Find by Attributes
        if params.query and len(params.query) > 0:
            counter = 1
            for obj_filter in params.query:
                if isinstance(obj_filter, dict):
                    for feature_idx, value_idxs in obj_filter.items():
                        if not feature_idx or not value_idxs:
                            msg = "feature_idx and value_idx in query can't be null"
                            messages.append(msg)
                            self._warn(WarningCode.FILTER_INVALID, f"q_{feature_idx}", msg)
                            continue
                        if feature_idx not in restrictions["filterable"]:
                            msg = f"feature_idx {feature_idx} is not filterable in channel"
                            messages.append(msg)
                            self._warn(WarningCode.FILTER_NOT_FILTERABLE, f"q_{feature_idx}", msg)
                            continue

                        feature_type = get_feature_type(feature_idx)

                        if feature_type not in [
                            FeatureType.SELECT,
                            FeatureType.MULTISELECT,
                            FeatureType.BOOL,
                            FeatureType.DECIMAL,
                        ]:
                            msg = f"feature_idx {feature_idx} can't be filtered by"
                            messages.append(msg)
                            self._warn(WarningCode.FILTER_UNSUPPORTED_TYPE, f"q_{feature_idx}", msg)
                        else:
                            # Feature
                            param_f = f"feature_{str(counter)}"
                            sql_params[param_f] = feature_idx

                            # Attribute
                            param_a = f"attr_{str(counter)}"

                            if feature_type in [FeatureType.BOOL]:
                                value_idxs = [str(value).capitalize() for value in value_idxs]

                            if feature_type in [FeatureType.DECIMAL]:
                                value_idxs = json.dumps(value_idxs)

                            sql_params[param_a] = value_idxs
                            if feature_idx in restrictions["features_filter_or"] and skip_or_filterable_features:
                                continue

                            if feature_type in [FeatureType.SELECT, FeatureType.MULTISELECT]:
                                if feature_idx in restrictions["features_filter_or"]:
                                    sql += f"AND pr.attributes_filter -> %({param_f})s ?| %({param_a})s "
                                else:
                                    sql += f"AND pr.attributes_filter -> %({param_f})s ?& %({param_a})s "
                            elif feature_type == FeatureType.BOOL:
                                # Handle boolean filtering with proper false logic
                                bool_conditions = []
                                for bool_val in value_idxs:
                                    if str(bool_val).lower() == "true" or bool_val is True:
                                        bool_conditions.append(f"(pr.attributes_filter->%({param_f})s)::jsonb ? 'True'")
                                    elif str(bool_val).lower() == "false" or bool_val is False:
                                        bool_conditions.append(
                                            f"(pr.attributes_filter->%({param_f})s IS NULL OR (pr.attributes_filter->%({param_f})s)::jsonb ? 'False')"
                                        )

                                if bool_conditions:
                                    sql += f"AND ({' OR '.join(bool_conditions)}) "
                            elif feature_type == FeatureType.DECIMAL:
                                sql += f"AND (pr.attributes_filter->%({param_f})s)::jsonb @> %({param_a})s::jsonb "

                        counter += 1

        if params.range and len(params.range) > 0:
            counter = 1
            for obj_filter in params.range:
                if isinstance(obj_filter, dict):
                    for feature_idx, value_tuple in obj_filter.items():
                        lesser_than = value_tuple[1]
                        greater_than = value_tuple[0]
                        if not feature_idx or (not greater_than and not lesser_than):
                            msg = "feature_idx and one of metric in query can't be null"
                            messages.append(msg)
                            self._warn(WarningCode.FILTER_INVALID, f"r_{feature_idx}", msg)
                            continue

                        if feature_idx in [Filtering.PRICE]:
                            sql_price = []
                            sql_range = []

                            check_is_price_for_verified = (
                                "AND NOT pp.is_only_for_verified_user" if not is_customer_verified else ""
                            )
                            if lesser_than:
                                param_a_lt = f"attr_{str(counter)}_lt"
                                sql_params[param_a_lt] = lesser_than
                                sql_price.append(f"pp.final_price <= %({param_a_lt})s {check_is_price_for_verified}")
                                sql_range.append(f"pp.range_from <= %({param_a_lt})s {check_is_price_for_verified}")

                            if greater_than:
                                param_a_gt = f"attr_{str(counter)}_gt"
                                sql_params[param_a_gt] = greater_than
                                sql_price.append(f"pp.final_price >= %({param_a_gt})s {check_is_price_for_verified}")
                                sql_range.append(f"pp.range_to >= %({param_a_gt})s {check_is_price_for_verified}")

                            sql += "AND ((" + " AND ".join(sql_price) + ") OR (" + " AND ".join(sql_range) + ")) "

                        else:
                            # numeric feature range (mass / temperature / length)
                            if feature_idx not in restrictions["filterable"]:
                                messages.append(f"feature_idx {feature_idx} is not rangeable in channel")
                                counter += 1
                                continue

                            # PIM owns the feature_type -> Unit class mapping (single source of truth)
                            _canonical_unit, unit_cls = get_feature(feature_idx).get_cls_unit_conversion()
                            if unit_cls is None:
                                messages.append(f"feature_idx {feature_idx} can't be filtered by range")
                                counter += 1
                                continue

                            param_f = f"range_feat_{counter}"
                            sql_params[param_f] = feature_idx
                            elem_conditions = []
                            if greater_than is not None:
                                param_gt = f"range_gt_{counter}"
                                sql_params[param_gt] = to_canonical(unit_cls, float(greater_than), language.iso2)
                                elem_conditions.append(f"e.val::numeric >= %({param_gt})s")
                            if lesser_than is not None:
                                param_lt = f"range_lt_{counter}"
                                sql_params[param_lt] = to_canonical(unit_cls, float(lesser_than), language.iso2)
                                elem_conditions.append(f"e.val::numeric <= %({param_lt})s")

                            if elem_conditions:
                                sql += (
                                    f"AND pr.attributes_filter ? %({param_f})s "
                                    "AND EXISTS (SELECT 1 FROM "
                                    f"jsonb_array_elements_text(pr.attributes_filter -> %({param_f})s) AS e(val) "
                                    f"WHERE {' AND '.join(elem_conditions)}) "
                                )

                        counter += 1

        # Search in name and sku
        if params.search:
            if not settings.MATRIX_FULL_TEXT_SEARCH:
                search = []
                for i, search_value in enumerate(params.search):
                    search_param = f"search_{i}"
                    original_value = search_value
                    if "%" in search_value:
                        search_value = search_value.replace("%", r"\%")

                    if "name" not in restrictions["searchable"]:
                        messages.append("name is not searchable in channel, only using SKU")
                    else:
                        search.append(f"pt.name ILIKE %({search_param})s")
                        sql_params[search_param] = f"%{search_value}%"
                    if "sku" not in restrictions["searchable"]:
                        messages.append("sku is not searchable in channel, did someone cleaned hardcode?")
                    else:
                        search.append(f"pr.sku ILIKE %({search_param})s")
                        sql_params[search_param] = f"%{search_value}%"

                    search.append(
                        f"EXISTS (SELECT 1 FROM jsonb_array_elements(pr.search) AS elem WHERE elem::text ILIKE %({search_param})s)"
                    )
                    search.append(
                        f"EXISTS (SELECT 1 FROM jsonb_array_elements(pr.tags) AS elem WHERE elem::text ILIKE %({search_param})s)"
                    )
                    search.append(
                        f"EXISTS (SELECT 1 FROM jsonb_array_elements(pt.subnames) AS elem WHERE elem::text ILIKE %({search_param})s)"
                    )
                    sql_params[search_param] = f"%{search_value}%"

                    if settings.MATRIX_FUZZY_SEARCH:
                        trgm_param = f"search_trgm_{i}"
                        sql_params[trgm_param] = original_value
                        if "name" in restrictions["searchable"]:
                            search.append(f"word_similarity(%({trgm_param})s, pt.name) > %(fuzzy_threshold)s")
                        if "sku" in restrictions["searchable"]:
                            search.append(f"word_similarity(%({trgm_param})s, pr.sku) > %(fuzzy_threshold)s")
                        search.append(
                            f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(pr.search) AS elem WHERE word_similarity(%({trgm_param})s, elem) > %(fuzzy_threshold)s)"
                        )
                        search.append(
                            f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(pr.tags) AS elem WHERE word_similarity(%({trgm_param})s, elem) > %(fuzzy_threshold)s)"
                        )
                        search.append(
                            f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(pt.subnames) AS elem WHERE word_similarity(%({trgm_param})s, elem) > %(fuzzy_threshold)s)"
                        )

                if settings.MATRIX_FUZZY_SEARCH:
                    sql_params["fuzzy_threshold"] = settings.MATRIX_FUZZY_SEARCH_THRESHOLD

                if len(search) > 0:
                    sql += f"AND ({' OR '.join(search)}) "
            else:
                lang_tsvector = lang_tsquery = None
                if MATRIX_FULL_TEXT_LANG_SEARCH:
                    lang_tsvector = self.prepare_weighted_tsvector(MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT, language)
                    lang_tsquery, tsquery_param, tsquery_param_value = self.prepare_tsquery(params.search, language)

                simple_tsvector = self.prepare_weighted_tsvector(MATRIX_PRODUCTS_FULL_TEXT_SEARCH_WEIGHT)
                simple_tsquery, tsquery_param, tsquery_param_value = self.prepare_tsquery(params.search)

                if lang_tsvector and lang_tsquery:
                    fts_clause = f"( {lang_tsvector} @@ {lang_tsquery} OR {simple_tsvector} @@ {simple_tsquery} )"
                else:
                    fts_clause = f"( {simple_tsvector} @@ {simple_tsquery} )"

                if settings.MATRIX_FUZZY_SEARCH:
                    trgm_parts = []
                    for i, sv in enumerate(params.search):
                        trgm_param = f"search_trgm_{i}"
                        sql_params[trgm_param] = sv
                        if "name" in restrictions["searchable"]:
                            trgm_parts.append(f"word_similarity(%({trgm_param})s, pt.name) > %(fuzzy_threshold)s")
                        trgm_parts.append(
                            f"EXISTS (SELECT 1 FROM jsonb_array_elements_text(pt.subnames) AS elem WHERE word_similarity(%({trgm_param})s, elem) > %(fuzzy_threshold)s)"
                        )
                    sql_params["fuzzy_threshold"] = settings.MATRIX_FUZZY_SEARCH_THRESHOLD
                    if trgm_parts:
                        sql += f"AND ({fts_clause} OR ({' OR '.join(trgm_parts)})) "
                    else:
                        sql += f"AND {fts_clause} "
                else:
                    sql += f"AND {fts_clause} "

                sql_params[tsquery_param] = tsquery_param_value

        # Order by
        orders = []
        counter = 1

        if custom_sort:
            orders.append(custom_sort)

        if params.sort and len(params.sort) > 0:
            for obj_filter in params.sort:
                if isinstance(obj_filter, dict):
                    for field, order in obj_filter.items():
                        if not field or not order:
                            msg = "feature_idx and order in sort can't be null"
                            messages.append(msg)
                            self._warn(WarningCode.SORT_INVALID, f"s_{field}", msg)
                            continue

                        # Check if field is a sortable feature_idx, if so handle it as sort_feature
                        if field in restrictions["sortable"] and field not in self.get_all_system_sort():
                            if not params.sort_feature:
                                params.sort_feature = []
                            params.sort_feature.append(obj_filter)
                        else:
                            # Handle as built-in sorting field
                            orders, messages = self.get_order_type(
                                channel, field, orders, self.get_asc_desc(order), messages, param=f"s_{field}"
                            )
                        counter += 1
        if params.sort_feature and len(params.sort_feature) > 0:
            for obj_filter in params.sort_feature:
                if isinstance(obj_filter, dict):
                    for feature_idx, order in obj_filter.items():
                        if not feature_idx or not order:
                            msg = "feature_idx and order in sort can't be null"
                            messages.append(msg)
                            self._warn(WarningCode.SORT_INVALID, f"s_{feature_idx}", msg)
                            continue

                        if feature_idx not in restrictions["sortable"]:
                            msg = f"feature_idx {feature_idx} is not sortable in channel"
                            messages.append(msg)
                            self._warn(WarningCode.SORT_NOT_SORTABLE, f"s_{feature_idx}", msg)
                            continue

                        feature_type = get_feature_type(feature_idx)
                        if feature_type in [
                            FeatureType.SELECT,
                            FeatureType.MULTISELECT,
                            FeatureType.TEXT,
                            FeatureType.DATETIME,
                            FeatureType.DECIMAL,
                        ]:
                            param_f = f"sort_{counter}"
                            sql_params[param_f] = feature_idx
                            if feature_type == FeatureType.DATETIME:
                                orders.append(
                                    f"(pr.attributes_filter ->> %({param_f})s)::timestamp {self.get_asc_desc(order)} NULLS LAST "
                                )
                            else:
                                orders.append(
                                    f"pr.attributes_filter -> %({param_f})s {self.get_asc_desc(order)} NULLS LAST "
                                )
                            orders.append(f"pr.attributes_filter -> %({param_f})s {self.get_asc_desc(order)} ")
                        elif feature_type in [FeatureType.MASS, FeatureType.TEMPERATURE, FeatureType.LENGTH]:
                            # value(s) stored as a list in attributes_filter (raw canonical, monotonic).
                            # ASC sorts by the lightest variant (MIN), DESC by the heaviest (MAX); for simple
                            # products the list has one element so MIN == MAX.
                            param_f = f"sort_{counter}"
                            sql_params[param_f] = feature_idx
                            direction = self.get_asc_desc(order)
                            aggregate = "MAX" if direction.strip().upper() == "DESC" else "MIN"
                            orders.append(
                                f"(SELECT {aggregate}(e.val::numeric) FROM "
                                f"jsonb_array_elements_text(pr.attributes_filter -> %({param_f})s) AS e(val)) "
                                f"{direction} NULLS LAST "
                            )
                        counter += 1

        if only_generate_sql and only_generate_minimal_sql:
            where_start = sql.find("WHERE")
            where_clause = sql[where_start:]
            t9n_join = ""
            if params.search:
                t9n_join = (
                    f"LEFT JOIN {self.app_name}_{self.t9n_table_name} AS pt "
                    f"ON pr.id = pt.product_representation_id AND pt.language_id = {language.pk} "
                )
            minimal_sql = (
                f"SELECT pr.sku, pp.final_price "
                f"FROM {self.app_name}_{self.product_table_name} AS pr "
                f"{sku_subquery_join}"
                f"{t9n_join}"
                f"LEFT JOIN {self.app_name}_{self.price_table_name} AS pp "
                f"ON pr.id = pp.product_representation_id "
                f"AND pp.currency_id = {currency.pk} AND pp.country_id = {country.pk} "
                f"{where_clause}"
            )
            return None, None, messages, (minimal_sql, sql_params), self._warnings

        has_category_ordering = params.category_url_key is not None
        should_apply_default_first = has_category_ordering and channel.prioritize_default_order

        if should_apply_default_first and apply_default_order and len(orders) == 0:
            if self._has_search_ranking:
                orders.append("search_rank DESC ")
                orders, messages, counter = self._apply_search_default_sort(
                    orders, channel, restrictions, sql_params, counter, messages
                )
            else:
                orders, messages = self.get_order_type(
                    channel, channel.default_order, orders, channel.default_order_direction, messages
                )

        if params.category_url_key:
            orders.append("pr.categories_position -> %(cat_url_key)s ASC ")
            # deterministic sort for categories, without it we can get different order (pagination) for the same category_position
            orders.append("pr.id ASC ")

        if len(orders) > 0:
            sql += f"ORDER BY {self.sep.join(orders)}"
        elif params.magento_id:
            magento_id_list = ",".join(map(str, params.magento_id))
            sql += f"ORDER BY array_position(ARRAY[{magento_id_list}]::integer[], pr.magento_id) "
        elif apply_default_order:
            if self._has_search_ranking:
                orders.append("search_rank DESC ")
                orders, messages, counter = self._apply_search_default_sort(
                    orders, channel, restrictions, sql_params, counter, messages
                )
                orders.append("pr.id ASC ")
                sql += f"ORDER BY {self.sep.join(orders)}"
            else:
                orders, messages = self.get_order_type(
                    channel, channel.default_order, orders, channel.default_order_direction, messages
                )
                sql += f"ORDER BY {self.sep.join(orders)}"

        count_pages = 0

        main_sql = sql
        main_sql_params = dict(sql_params)

        if limit_offset:
            main_sql += " LIMIT %(limit)s OFFSET %(offset)s"
            main_sql_params["limit"] = params.limit
            main_sql_params["offset"] = params.offset()

        if only_generate_sql:
            return None, None, messages, (main_sql, main_sql_params), self._warnings

        use_parallel = MATRIX_PRODUCTS_PARALLEL_QUERIES
        if (
            use_parallel
            and (
                settings.PAGINATION_TYPE == PaginationType.FULL_PAGES
                or settings.PAGINATION_TYPE == PaginationType.X_PAGES
            )
            and not params.search_window
            and limit_offset
        ):
            if settings.PAGINATION_TYPE == PaginationType.FULL_PAGES:
                count_sql = f"SELECT count(*) FROM ({sql}) as licz"
                count_sql_params = dict(sql_params)
            else:
                count_sql = f"SELECT count(*) FROM ({sql}) as licz"
                count_sql_params = dict(sql_params)
                count_sql_params["limit"] = params.limit * settings.PAGINATION_NEXT_PAGES_COUNT

            try:
                products, count_pages = self.execute_parallel_queries(
                    main_sql, main_sql_params, count_sql, count_sql_params
                )
            except Exception:
                products = self.fetch_all(main_sql, main_sql_params)
                if settings.PAGINATION_TYPE == PaginationType.FULL_PAGES:
                    count_pages = self.count_full_pages(sql, sql_params)
                else:
                    count_pages = self.count_x_pages(sql, sql_params, settings.PAGINATION_NEXT_PAGES_COUNT)
        else:
            products = self.fetch_all(main_sql, main_sql_params)

            if (
                (
                    settings.PAGINATION_TYPE == PaginationType.FULL_PAGES
                    or settings.PAGINATION_TYPE == PaginationType.X_PAGES
                )
                and not params.search_window
                and limit_offset
            ):
                if settings.PAGINATION_TYPE == PaginationType.FULL_PAGES:
                    count_pages = self.count_full_pages(sql, sql_params)
                else:
                    count_pages = self.count_x_pages(sql, sql_params, settings.PAGINATION_NEXT_PAGES_COUNT)

        return products, count_pages, messages, None, self._warnings
