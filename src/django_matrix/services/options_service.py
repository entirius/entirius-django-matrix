# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Options service — wraps options repository, pre-groups response for v2."""

from django_matrix.models import Channel
from django_matrix.repository.raw_sql.options import Options as OptionsRepository
from django_matrix.repository.raw_sql.product import Product as ProductRepository
from django_matrix.services.product_service import build_query_filters, build_range_filters


def get_options(
    channel: Channel,
    language,
    currency,
    country,
    category: str | None = None,
    filters: dict | None = None,
    ranges: dict | None = None,
    show_zeros: bool = False,
) -> dict:
    """Returns pre-grouped options: {sort: [], ranges: [], filters: []}."""
    from django_matrix.utils.params import OptionsQuery

    params = OptionsQuery(
        language=language.iso2 if language else None,
        currency=currency.iso3 if currency else None,
        country=country.iso2 if country else None,
        category_url_key=category,
        query=build_query_filters(filters) if filters else None,
        range=build_range_filters(ranges) if ranges else None,
        show_zeros=show_zeros,
    )

    # Get SQL for filtered products (options counts are context-sensitive)
    _, _, _, (products_sql, products_sql_params), *_ = ProductRepository().find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=False,
        skip_or_filterable_features=True,
        only_generate_sql=True,
        only_generate_minimal_sql=True,
    )

    # Build v1 flat options
    v1_options = OptionsRepository(
        params=params, channel=channel, language=language, currency=currency, country=country
    ).build_filter_options(products_sql=products_sql, products_sql_params=products_sql_params)

    # Pre-group into v2 structure
    return _pregroup_options(v1_options)


def _pregroup_options(v1_options: list[dict]) -> dict:
    """Convert v1 flat list into v2 pre-grouped {sort, ranges, filters}."""
    sort_options = []
    range_filters = []
    select_filters = []

    for option in v1_options:
        filter_type = option.get("filter_type", "Default")
        idx = option.get("idx", "")

        if filter_type == "order_by":
            for sub_option in option.get("options", []):
                sort_options.append(
                    {
                        "idx": sub_option.get("idx"),
                        "label": sub_option.get("label"),
                        "position": sub_option.get("position", 0),
                    }
                )
        elif filter_type == "Slide" or "min_value" in option:
            range_filters.append(
                {
                    "idx": idx,
                    "label": option.get("label", idx),
                    "position": option.get("position", 0),
                    "min": float(option["min_value"]) if option.get("min_value") else None,
                    "max": float(option["max_value"]) if option.get("max_value") else None,
                }
            )
        else:
            widget_type = _map_filter_type(filter_type)
            values = []
            for v in option.get("options", []):
                values.append(
                    {
                        "idx": v.get("idx"),
                        "label": v.get("label"),
                        "count": v.get("products_count", 0),
                        "position": v.get("position", 0),
                        "extension": v.get("extension"),
                    }
                )
            select_filters.append(
                {
                    "idx": idx,
                    "label": option.get("label", idx),
                    "widget_type": widget_type,
                    "position": option.get("position", 0),
                    "is_or_filter": option.get("is_or_filter", False),
                    "values": values,
                }
            )

    return {"sort": sort_options, "ranges": range_filters, "filters": select_filters}


def _map_filter_type(v1_type: str) -> str:
    """Map v1 filter_type string to v2 widget_type."""
    mapping = {
        "Default": "default",
        "Swatch_Image": "swatch_image",
        "Swatch_Text": "swatch_text",
        "Slide": "slide",
        "Boolean": "boolean",
        "Radio_Text": "radio_text",
    }
    return mapping.get(v1_type, "default")
