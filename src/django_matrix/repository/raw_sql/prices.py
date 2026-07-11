# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_regional.models import Country, Currency, Language

from django_matrix.models import Channel
from django_matrix.repository.raw_sql import DbConnect
from django_matrix.utils.params import PriceQuery


class ProductPrice(DbConnect):
    app_name = "django_matrix"
    product_table_name = "productrepresentation"
    t9n_table_name = "productt9n"
    price_table_name = "productprice"
    sep = ","

    def find_by_api_query(
        self,
        params: PriceQuery,
        channel: "Channel",
        language: "Language",
        country: "Country",
        currency: "Currency",
        is_customer_verified: bool,
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

        sql_params = {"channel_id": channel.pk}

        sql = (
            f"SELECT pp.is_range, pp.has_special_price, pp.price, pp.range_from, pp.range_to, pp.promo_badge, "
            f"pp.special_from_date, pp.special_to_date, pp.special_price, pp.special_price_range_from, pp.special_price_range_to, "
            f"pp.tax_amount, pp.tax_rule, pp.price_tax_config_opposite, pp.price_tax_config_opposite_from, pp.price_tax_config_opposite_to, "
            f"pp.is_only_for_verified_user, "
            f"pp.special_price_tax_config_opposite_from, pp.special_price_tax_config_opposite_to, pp.special_price_tax_config_opposite, "
            f"pp.is_price_offer, pp.max_price_offer, pp.min_price_offer, "
            f"pp.omnibus_price, pp.omnibus_price_from, pp.omnibus_price_to, "
            f"pt.url_key, "
            f"pr.sku "
            f"FROM {self.app_name}_{self.price_table_name} AS pp "
            f"LEFT JOIN {self.app_name}_{self.product_table_name} AS pr "
            f"ON pp.product_representation_id = pr.id AND pp.currency_id = {currency.pk} AND pp.country_id = {country.pk} "
            f"LEFT JOIN {self.app_name}_{self.t9n_table_name} AS pt "
            f"ON pp.product_representation_id = pt.product_representation_id AND pt.language_id = {language.pk} "
            f"WHERE pr.channel_id = %(channel_id)s "
        )

        # Filter by is_customer_verified
        if not is_customer_verified:
            sql += "AND NOT (pp.is_only_for_verified_user AND NOT %(is_customer_verified)s) "
            sql_params["is_customer_verified"] = is_customer_verified
            messages.append("Your are not verified customer and query may be limited")

        # Find by Product URL KEY
        if params.url_key:
            if len(params.url_key) > 1:
                url_keys = split_list(params.url_key, "url_key")
                sql += f"AND pr.url_keys ?| array[{self.sep.join(url_keys)}] "
            elif len(params.url_key) == 1:
                sql += "AND pr.url_keys ? %(url_key)s "
                sql_params["url_key"] = params.url_key[0]

        # Find by SKU
        if params.sku:
            skus = split_list(params.sku, "sku")
            sql += f"AND pr.sku IN ({self.sep.join(skus)}) "

        sql += "ORDER BY pr.id ASC "

        # Main query
        prices = self.fetch_all(sql, sql_params)
        return prices, messages
