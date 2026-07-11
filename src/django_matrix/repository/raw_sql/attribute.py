# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_regional.models import Language

from django_matrix.models import Channel
from django_matrix.repository.raw_sql import DbConnect
from django_matrix.settings import BLACKLISTED_FEATURES_IDX_VISIBILITY, VISIBILITY_MECHANISM
from django_matrix.utils.params import AttributeQuery


class Attribute(DbConnect):
    app_name = "django_matrix"
    attribute_table_name = "attribute"
    product_table_name = "productrepresentation"
    sep = ","

    def find_by_api_query(
        self,
        params: AttributeQuery,
        channel: "Channel",
        language: "Language",
        feature_type: str = None,
        is_full_view: bool = False,
        use_full_data_features: bool = False,
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

        sql_params = {"channel_id": channel.pk, "language": language.iso2}

        visibility_table = (
            "django_matrix_fulldatafeatures" if use_full_data_features else "django_matrix_visibilityfeatures"
        )

        sql = (
            f"SELECT pr.sku, "
            f"a.feature_idx, a.feature_name_t9n ->> %(language)s AS feature_name, a.feature_type, "
            f"a.attribute_idx, a.attribute_value_text, a.attribute_value_json, a.attribute_value_t9n ->> %(language)s AS attribute_value, "
            f"a.attribute_value_json ->> %(language)s AS attribute_value_json_t9n, "
            f"a.extension "
            f"FROM {self.app_name}_{self.attribute_table_name} AS a "
            f"LEFT JOIN {self.app_name}_{self.product_table_name} AS pr "
            f"ON a.product_id = pr.id "
            f"LEFT JOIN ( "
            f"SELECT f.idx FROM {visibility_table} vf "
            f"LEFT JOIN django_pim_feature f ON f.id = vf.feature_id "
            f"WHERE vf.channel_id = %(channel_id)s "
            f") AS vis ON vis.idx = a.feature_idx "
            f"LEFT JOIN django_pim_feature f ON f.idx = a.feature_idx "
            f"WHERE pr.channel_id = %(channel_id)s "
        )

        # This is for visibility mechanism
        # 1 - Get all features from visibilityfeatures table per channel (default)
        # 2 - Get all features instead of BLACKLISTED_FEATURES_IDX_VISIBLITY

        # Find by SKU
        if params.sku:
            skus = split_list(params.sku, "sku")
            sql += f"AND pr.sku IN ({self.sep.join(skus)}) "

        # zwróć wszystkie atrybuty widoczne (ustawione w channel) chyba, że ktoś sprecyzuje feature_type
        if params.only_custom:
            sql += "AND a.feature_is_for_customization = TRUE "
            sql += "AND a.feature_type IN ('SELECT', 'MULTISELECT') "
        elif feature_type:
            sql_params["type_a"] = feature_type
            sql += "AND a.feature_type = %(type_a)s "
        else:
            if VISIBILITY_MECHANISM == 1 or not is_full_view:
                sql += "AND vis.idx IS NOT NULL "
            elif VISIBILITY_MECHANISM == 2:
                if BLACKLISTED_FEATURES_IDX_VISIBILITY:
                    features = split_list(BLACKLISTED_FEATURES_IDX_VISIBILITY, "feature")
                    sql += f"AND a.feature_idx NOT IN ({self.sep.join(features)}) "

        sql += "ORDER BY f.display_order ASC, a.feature_name_t9n ->> %(language)s ASC "

        # Main query
        attributes = self.fetch_all(sql, sql_params)

        return attributes, messages
