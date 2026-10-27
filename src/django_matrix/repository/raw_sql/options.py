# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Any

from django_pim.models import Feature, FeatureTypeEnum
from django_regional.models import Country, Currency, Language

from django_matrix.dto.view import (
    ComparableFeature,
    FilterGroup,
    SortOption,
)
from django_matrix.models import Channel
from django_matrix.repository.raw_sql import DbConnect
from django_matrix.utils import bool_translate
from django_matrix.utils.options_getter import (
    CREATED_AT_SORT_LABEL_LANGS,
    CREATED_AT_SORT_POSITION,
    PRICE_FILTER_LABEL_LANGS,
    PRICE_FILTER_POSITION,
    PRICE_SORT_LABEL_LANGS,
    PRICE_SORT_POSITION,
    SORT_LABEL_LANGS,
    SORT_POSITION,
)
from django_matrix.utils.params import OptionsQuery
from django_matrix.utils.unit_options import convert_bounds_for_lang


class Options(DbConnect):
    app_name = "django_pim"
    params = None
    channel = None
    language = None
    currency = None
    country = None

    def __init__(
        self, params: OptionsQuery, channel: Channel, language: Language, currency: Currency, country: Country
    ):
        self.params = params
        self.channel = channel
        self.language = language
        self.currency = currency
        self.country = country
        self.result_data = []
        self.price_range: tuple[float, float] | None = None
        self.base_sql_params = {
            "channel_id": self.channel.pk,
            "language_iso": self.language.iso2,
            "bool_type": FeatureTypeEnum.BOOL,
            "select_type": FeatureTypeEnum.SELECT,
            "multiselect_type": FeatureTypeEnum.MULTISELECT,
            "decimal_type": FeatureTypeEnum.DECIMAL,
        }

    def get_comparable_features(
        self,
        channel: "Channel",
        language: "Language",
    ) -> list[ComparableFeature]:
        """Get comparable/orderable features for sorting options"""

        sql_params = {
            "channel_id": channel.pk,
            "language_iso": language.iso2,
        }

        sql = """
        SELECT 
            f.idx as feature_idx,
            f.name_t9n->>%(language_iso)s as feature_name,
            ccf.position
        FROM django_matrix_sortablefeatures ccf
        JOIN django_pim_feature f ON ccf.feature_id = f.id
        WHERE ccf.channel_id = %(channel_id)s
        ORDER BY ccf.position
        """

        data = self.fetch_all(sql, sql_params)
        return ComparableFeature.comparable_features_collection(data)

    def _get_filter_type_label(self, filter_type: int) -> str:
        """Convert filter type ID to label"""
        filter_type_map = {
            0: "Default",
            1: "Swatch_Image",
            2: "Swatch_Text",
            3: "Slide",
            4: "Boolean",
            5: "Radio_Text",
        }
        return filter_type_map.get(filter_type, "Default")

    def _fetch_price_range(self, products_sql: str | None, products_sql_params: dict | None) -> None:
        if products_sql and products_sql_params:
            price_sql = f"""
            SELECT 
                MIN(final_price) as min_price,
                MAX(final_price) as max_price
            FROM ({products_sql}) AS filtered_products
            WHERE final_price IS NOT NULL AND final_price > 0
            """
            price_result = self.fetch_all(price_sql, products_sql_params)
            if price_result and price_result[0]["min_price"] is not None:
                self.price_range = (price_result[0]["min_price"], price_result[0]["max_price"])

    def _fetch_features_metadata(
        self, products_sql: str | None, products_sql_params: dict | None
    ) -> list[dict[str, Any]]:

        metadata_sql = """
        SELECT 
            f.idx as feature_idx,
            f.name_t9n->>%(language_iso)s as feature_name,
            f.filter_type,
            cf.position,
            cf.is_or_filter,
            a.idx as attribute_idx,
            a.name_t9n->>%(language_iso)s as attribute_name,
            a.display_order,
            a.extension,
            f.feature_type
        FROM django_matrix_filterablefeatures cf
        JOIN django_pim_feature f ON cf.feature_id = f.id
        JOIN django_pim_attribute a ON a.feature_id = f.id
        WHERE cf.channel_id = %(channel_id)s
          AND f.feature_type IN (%(select_type)s, %(multiselect_type)s)
        UNION ALL
        SELECT 
            f.idx as feature_idx,
            f.name_t9n->>%(language_iso)s as feature_name,
            f.filter_type,
            cf.position,
            cf.is_or_filter,
            'true' as attribute_idx,
            NULL as attribute_name,
            1 as display_order,
            NULL as extension,
            %(bool_type)s as feature_type
        FROM django_matrix_filterablefeatures cf
        JOIN django_pim_feature f ON cf.feature_id = f.id
        WHERE cf.channel_id = %(channel_id)s AND f.feature_type = %(bool_type)s
        UNION ALL
        SELECT 
            f.idx as feature_idx,
            f.name_t9n->>%(language_iso)s as feature_name,
            f.filter_type,
            cf.position,
            cf.is_or_filter,
            'false' as attribute_idx,
            NULL as attribute_name,
            2 as display_order,
            NULL as extension,
            %(bool_type)s as feature_type
        FROM django_matrix_filterablefeatures cf
        JOIN django_pim_feature f ON cf.feature_id = f.id
        WHERE cf.channel_id = %(channel_id)s AND f.feature_type = %(bool_type)s
        UNION ALL
        SELECT
            f.idx as feature_idx,
            f.name_t9n->>%(language_iso)s as feature_name,
            f.filter_type,
            cf.position,
            cf.is_or_filter,
            NULL as attribute_idx,
            NULL as attribute_name,
            0 as display_order,
            NULL as extension,
            %(decimal_type)s as feature_type
        FROM django_matrix_filterablefeatures cf
        JOIN django_pim_feature f ON cf.feature_id = f.id
        WHERE cf.channel_id = %(channel_id)s AND f.feature_type = %(decimal_type)s
        ORDER BY position, feature_idx, display_order, attribute_idx
        """

        features_metadata = self.fetch_all(metadata_sql, self.base_sql_params)
        return features_metadata

    def _calculate_filter_conditions_for_query(self, bool_feature_idxs: set[str]) -> tuple[list[str], dict[str, Any]]:
        sql_params = self.base_sql_params.copy()
        filter_conditions = []
        if self.params.query:
            i = 0
            for query_filter in self.params.query:
                for feature_idx, value_idx in query_filter.items():
                    feature_param = f"filter_feature_{i}"
                    attributes_param = f"filter_attrs_{i}"
                    sql_params[feature_param] = feature_idx
                    # attributes_filter stores BOOL values capitalized ("True"/"False"); mirror product.py:288
                    if feature_idx in bool_feature_idxs:
                        value_idx = [str(value).capitalize() for value in value_idx]
                    sql_params[attributes_param] = value_idx
                    filter_conditions.append(f"(bp.attributes_filter -> %({feature_param})s ?| %({attributes_param})s)")
                    i += 1
        return filter_conditions, sql_params

    def _merge_count_with_metadata(
        self, features_metadata: list[dict[str, Any]], count_lookup: dict[tuple[str, str], int]
    ) -> dict[str, FilterGroup]:
        grouped_features = {}
        for feature in features_metadata:
            if feature.get("feature_type") == FeatureTypeEnum.DECIMAL:
                continue
            # group by feature_idx to add options to the same feature_idx
            if feature["feature_idx"] not in grouped_features:
                filter_group = FilterGroup.factory(
                    feature["position"],
                    feature["feature_idx"],
                    self._get_filter_type_label(feature["filter_type"]),
                    [],
                    feature["feature_name"] or feature["feature_idx"],
                )
                grouped_features[feature["feature_idx"]] = filter_group

            count = count_lookup.get((feature["feature_idx"], feature["attribute_idx"]), 0)
            if feature["attribute_idx"]:
                show_zeros = self.params.show_zeros if self.params.show_zeros is not None else False
                if show_zeros or count > 0:
                    label = feature["attribute_name"] or feature["attribute_idx"]
                    if feature.get("feature_type") == FeatureTypeEnum.BOOL:
                        label = bool_translate(
                            (
                                feature["attribute_idx"].lower()
                                if isinstance(feature["attribute_idx"], str)
                                else feature["attribute_idx"]
                            ),
                            self.language.iso2,
                        )

                    idx_value = feature["attribute_idx"]
                    if feature.get("feature_type") == FeatureTypeEnum.BOOL and isinstance(idx_value, str):
                        if idx_value.lower() == "true":
                            idx_value = True
                        elif idx_value.lower() == "false":
                            idx_value = False

                    filter_option_data = {
                        "position": feature["display_order"],
                        "label": label,
                        "idx": idx_value,
                        "products_count": count,
                        "extension": feature["extension"],
                    }
                    grouped_features[feature["feature_idx"]].options.append(filter_option_data)
        return grouped_features

    def get_filterable_features(
        self, products_sql: str | None = None, products_sql_params: dict | None = None
    ) -> dict[str, FilterGroup]:
        """Optimized version with better query structure for large datasets"""

        features_metadata = self._fetch_features_metadata(products_sql, products_sql_params)
        bool_feature_idxs = {
            f["feature_idx"] for f in features_metadata if f.get("feature_type") == FeatureTypeEnum.BOOL
        }
        filter_conditions, sql_params = self._calculate_filter_conditions_for_query(bool_feature_idxs)

        # Create base filtered products CTE for reuse
        base_products_cte = ""
        if products_sql and products_sql_params:
            sql_params.update(products_sql_params)
            base_products_cte = f"""
            WITH base_products AS (
                SELECT DISTINCT pr.id as pr_id, pr.sku, pr.attributes_filter
                FROM ({products_sql}) AS filtered_products
                JOIN django_matrix_productrepresentation pr ON filtered_products.sku = pr.sku
                WHERE pr.channel_id = %(channel_id)s
            ),
            """
        else:
            base_products_cte = """
            WITH base_products AS (
                SELECT id as pr_id, sku, attributes_filter
                FROM django_matrix_productrepresentation
                WHERE channel_id = %(channel_id)s
            ),
            """

        # Optimize filter condition evaluation
        cond_sql = " AND ".join(filter_conditions) if filter_conditions else "TRUE"

        count_sql = f"""
        {base_products_cte}
        filterable_features AS (
            SELECT cf.feature_id, f.idx as feature_idx, f.feature_type, cf.is_or_filter
            FROM django_matrix_filterablefeatures cf
            JOIN django_pim_feature f ON cf.feature_id = f.id
            WHERE cf.channel_id = %(channel_id)s
        )
        SELECT
            feature_idx,
            attribute_idx,
            is_or_filter,
            COUNT(DISTINCT pr_id) as product_count
        FROM (
            -- SELECT/MULTISELECT features - optimized by extracting JSONB values directly
            SELECT DISTINCT
                ff.feature_idx,
                attr_val as attribute_idx,
                ff.is_or_filter,
                bp.pr_id
            FROM filterable_features ff
            JOIN base_products bp ON (
                ff.feature_type IN (%(select_type)s, %(multiselect_type)s)
                AND (
                    ff.is_or_filter = TRUE
                    OR ({cond_sql})
                )
                AND bp.attributes_filter ? ff.feature_idx
            )
            CROSS JOIN LATERAL jsonb_array_elements_text(bp.attributes_filter->ff.feature_idx) AS attr_val

            UNION ALL

            -- BOOLEAN features - optimized without CROSS JOIN
            SELECT DISTINCT
                ff.feature_idx,
                CASE WHEN COALESCE(pa.value_bool, false) = true THEN 'true' ELSE 'false' END as attribute_idx,
                ff.is_or_filter,
                bp.pr_id
            FROM filterable_features ff
            JOIN base_products bp ON ff.feature_type = %(bool_type)s
            LEFT JOIN django_pim_realproduct rp ON bp.sku = rp.sku
            LEFT JOIN django_pim_product p ON p.real_product_id = rp.id
            LEFT JOIN django_pim_productattribute pa ON (
                pa.feature_id = ff.feature_id
                AND pa.product_id = p.id
            )
            WHERE (
                ff.is_or_filter = TRUE
                OR ({cond_sql})
            )
        ) AS combined
        GROUP BY feature_idx, attribute_idx, is_or_filter
        """

        counts = self.fetch_all(count_sql, sql_params)
        self._fetch_price_range(products_sql, products_sql_params)
        count_lookup = {
            (count_row["feature_idx"], count_row["attribute_idx"]): count_row["product_count"] for count_row in counts
        }
        grouped_features = self._merge_count_with_metadata(features_metadata, count_lookup)

        decimal_ranges = self._fetch_decimal_ranges(base_products_cte, sql_params)
        for feature in features_metadata:
            if feature["feature_type"] != FeatureTypeEnum.DECIMAL:
                continue
            idx = feature["feature_idx"]
            if idx in decimal_ranges and idx not in grouped_features:
                min_val, max_val = decimal_ranges[idx]
                grouped_features[idx] = FilterGroup.factory(
                    feature["position"],
                    idx,
                    "Slide",
                    None,
                    feature["feature_name"] or idx,
                    min_val,
                    max_val,
                )

        return grouped_features

    def _fetch_decimal_ranges(
        self, base_products_cte: str, sql_params: dict[str, Any]
    ) -> dict[str, tuple[float, float]]:
        """Fetch min/max ranges for DECIMAL filterable features."""
        range_sql = f"""
        {base_products_cte}
        decimal_features AS (
            SELECT cf.feature_id, f.idx as feature_idx
            FROM django_matrix_filterablefeatures cf
            JOIN django_pim_feature f ON cf.feature_id = f.id
            WHERE cf.channel_id = %(channel_id)s
              AND f.feature_type = %(decimal_type)s
        )
        SELECT
            feature_idx,
            MIN(val) as min_val,
            MAX(val) as max_val
        FROM decimal_features df
        JOIN base_products bp ON bp.attributes_filter ? df.feature_idx
        CROSS JOIN LATERAL jsonb_array_elements_text(bp.attributes_filter->df.feature_idx) AS t(raw_val)
        CROSS JOIN LATERAL (SELECT raw_val::numeric AS val) AS n
        GROUP BY feature_idx
        HAVING MIN(val) != MAX(val)
        """
        rows = self.fetch_all(range_sql, sql_params)
        return {row["feature_idx"]: (float(row["min_val"]), float(row["max_val"])) for row in rows}

    def _get_filter_options(self, products_sql: str | None, products_sql_params: dict | None) -> None:
        features_data = self.get_filterable_features(products_sql=products_sql, products_sql_params=products_sql_params)
        grouped_features = {
            k: v
            for k, v in features_data.items()
            if (v.options and len(v.options) > 0) or v.min_value is not None or self.params.show_zeros
        }
        for group_data in grouped_features.values():
            self.result_data.append(group_data)

    def _add_price_range(self) -> None:
        if (label := PRICE_FILTER_LABEL_LANGS.get(self.language.iso2, None)) and self.price_range:
            price_filter = FilterGroup.factory(
                PRICE_FILTER_POSITION, "price", "Slide", None, label, self.price_range[0], self.price_range[1]
            )
            self.result_data.append(price_filter)

    def _fetch_numeric_feature_min_max(
        self, feature_idx: str, products_sql: str | None, products_sql_params: dict | None
    ) -> tuple[float, float] | None:
        sql_params = {"nf_idx": feature_idx}
        if products_sql and products_sql_params:
            sql_params.update(products_sql_params)
            sql = f"""
            SELECT MIN(e.val::numeric) as min_v, MAX(e.val::numeric) as max_v
            FROM ({products_sql}) AS filtered_products
            JOIN django_matrix_productrepresentation pr ON filtered_products.sku = pr.sku
            CROSS JOIN LATERAL jsonb_array_elements_text(pr.attributes_filter -> %(nf_idx)s) AS e(val)
            WHERE pr.attributes_filter ? %(nf_idx)s
            """
        else:
            sql_params["channel_id"] = self.channel.pk
            sql = """
            SELECT MIN(e.val::numeric) as min_v, MAX(e.val::numeric) as max_v
            FROM django_matrix_productrepresentation pr
            CROSS JOIN LATERAL jsonb_array_elements_text(pr.attributes_filter -> %(nf_idx)s) AS e(val)
            WHERE pr.channel_id = %(channel_id)s AND pr.attributes_filter ? %(nf_idx)s
            """
        result = self.fetch_all(sql, sql_params)
        if not result or result[0]["min_v"] is None:
            return None
        return result[0]["min_v"], result[0]["max_v"]

    def _add_numeric_feature_ranges(self, products_sql: str | None, products_sql_params: dict | None) -> None:
        """Mass / temperature / length filterable features -> Slide range in the language's unit."""
        meta_sql = """
        SELECT
            f.idx as feature_idx,
            f.name_t9n->>%(language_iso)s as feature_name,
            f.feature_type,
            cf.position
        FROM django_matrix_filterablefeatures cf
        JOIN django_pim_feature f ON cf.feature_id = f.id
        WHERE cf.channel_id = %(channel_id)s
          AND f.feature_type IN (%(mass_type)s, %(temperature_type)s, %(length_type)s)
        ORDER BY cf.position
        """
        meta_params = {
            **self.base_sql_params,
            "mass_type": FeatureTypeEnum.MASS,
            "temperature_type": FeatureTypeEnum.TEMPERATURE,
            "length_type": FeatureTypeEnum.LENGTH,
        }

        for feature in self.fetch_all(meta_sql, meta_params):
            min_max = self._fetch_numeric_feature_min_max(feature["feature_idx"], products_sql, products_sql_params)
            if min_max is None:
                continue
            if min_max[0] == min_max[1]:
                # A slider with both ends on the same value filters nothing and renders as a dead
                # control — that is what a category holding a single product with the feature gives.
                # DECIMAL ranges drop these in SQL (HAVING MIN != MAX); this path drops them here.
                continue
            _canonical_unit, unit_cls = Feature.objects.get(idx=feature["feature_idx"]).get_cls_unit_conversion()
            if unit_cls is None:
                continue
            min_value, max_value, unit = convert_bounds_for_lang(
                unit_cls, float(min_max[0]), float(min_max[1]), self.language.iso2
            )
            self.result_data.append(
                FilterGroup.factory(
                    feature["position"],
                    feature["feature_idx"],
                    "Slide",
                    None,
                    feature["feature_name"] or feature["feature_idx"],
                    min_value,
                    max_value,
                    unit=unit,
                )
            )

    def _get_sortable_feature_idxs_with_values(
        self,
        candidate_idxs: list[str],
        products_sql: str | None,
        products_sql_params: dict | None,
    ) -> set[str]:
        """Return the subset of ``candidate_idxs`` for which at least one product in the
        current (filtered) result set actually has a value stored in ``attributes_filter``.

        Sorting relies on ``pr.attributes_filter -> feature_idx``; a feature that no product
        in the category has a value for cannot be sorted by, so it must be hidden."""
        if not candidate_idxs:
            return set()

        sql_params: dict[str, Any] = {"sortable_idxs": list(candidate_idxs)}
        if products_sql and products_sql_params:
            sql_params.update(products_sql_params)
            products_source = f"({products_sql}) AS filtered_products"
            join_condition = "filtered_products.sku = pr.sku"
        else:
            sql_params["channel_id"] = self.channel.pk
            products_source = "django_matrix_productrepresentation pr_filter"
            join_condition = "pr_filter.sku = pr.sku AND pr.channel_id = %(channel_id)s"

        sql = f"""
        SELECT idx
        FROM unnest(%(sortable_idxs)s::text[]) AS idx
        WHERE EXISTS (
            SELECT 1
            FROM {products_source}
            JOIN django_matrix_productrepresentation pr ON {join_condition}
            WHERE pr.attributes_filter ? idx
        )
        """
        return {row["idx"] for row in self.fetch_all(sql, sql_params)}

    def _sort_options(self, products_sql: str | None, products_sql_params: dict | None) -> None:
        comparable_features = self.get_comparable_features(channel=self.channel, language=self.language)
        idxs_with_values = self._get_sortable_feature_idxs_with_values(
            [feature.feature_idx for feature in comparable_features], products_sql, products_sql_params
        )
        sort_options = []
        for feature in comparable_features:
            if feature.feature_idx not in idxs_with_values:
                continue
            sort_option = SortOption.factory(feature.position, feature.feature_idx, feature.feature_name)
            sort_options.append(sort_option)

        if label := CREATED_AT_SORT_LABEL_LANGS.get(self.language.iso2, None):
            created_sort = SortOption.factory(CREATED_AT_SORT_POSITION, "db_created", label)
            sort_options.append(created_sort)

        if label := PRICE_SORT_LABEL_LANGS.get(self.language.iso2, None):
            price_sort = SortOption.factory(PRICE_SORT_POSITION, "price", label)
            sort_options.append(price_sort)

        if (label := SORT_LABEL_LANGS.get(self.language.iso2, None)) and sort_options:
            sort_filter = FilterGroup.factory(SORT_POSITION, "order_by", "order_by", sort_options, label)
            self.result_data.append(sort_filter)

    def build_filter_options(
        self,
        products_sql: str | None = None,
        products_sql_params: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Build complete filter options response"""

        self._get_filter_options(products_sql, products_sql_params)
        self._add_price_range()
        self._add_numeric_feature_ranges(products_sql, products_sql_params)
        self._sort_options(products_sql, products_sql_params)
        self.result_data.sort(key=lambda x: x.position)
        return [filter_group.asdict() for filter_group in self.result_data]
