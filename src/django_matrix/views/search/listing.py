# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import logging

from django.conf import settings
from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import BadRequest
from django_utils.api.responses import PaginatedResponse
from magento2_sdk2.dto.search import SearchParameters
from magento2_sdk2.services.client import Magento2Client
from magento2_sdk2.services.worker import search

from django_matrix.dto.view.product import product_collection
from django_matrix.repository.raw_sql.product import Product as ProductRepository
from django_matrix.settings import MAGENTO_TOKEN, MAGENTO_URL
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import MagentoQuery, get_view_variable_from_kwargs

logger_process = logging.getLogger("process")


def get_id_list_from_magento(params):
    """
    Function with params which use magento2_sdk2 and endpoint search to get id_list return it.
    """
    if not MAGENTO_URL or not MAGENTO_TOKEN:
        raise BadRequest("Configure Magento settings")
    if not params.search_text:
        raise BadRequest("Need to specify search_text")

    current_page = params.current_page - 1 if params.current_page != 0 else params.current_page
    magento_client: Magento2Client = Magento2Client(base_url=MAGENTO_URL, access_token=MAGENTO_TOKEN)

    text_search = params.search_text

    if not params.search_text.startswith("'") and not params.search_text.startswith('"'):
        text_search = '"' + text_search
    if not params.search_text.endswith("'") and not params.search_text.endswith('"'):
        text_search = text_search + '"'

    search_params_obj = SearchParameters(
        search_text=text_search,
        price_from=params.price_from,
        price_to=params.price_to,
        category_ids=params.category_ids,
        visibility=params.visibility,
        page_size=params.page_size,
        current_page=current_page,
    )
    try:
        response = search(magento_client, search_params_obj)
        if settings.DEBUG:
            logger_process.info("Search request send to magento", extra={"details": {"response": response}})
    except Exception as e:
        logger_process.error(
            f"{e}",
            extra={"details": {"params": params}},
        )
        raise BadRequest("Magento error. Check process log file")
    if response["items"]:
        id_list = [magento_id.get("id") for magento_id in response["items"]]
    else:
        id_list = []
    return id_list, response.get("total_count", len(id_list))


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(MagentoQuery.Schema())
@prepare_view
def search_listing_view(request, params: MagentoQuery, *args, **kwargs) -> "PaginatedResponse":
    """Returns a paginated response with a list of products"""
    # These variables are prepared by prepare_view decorator. Dont mess with this
    id_list, total_count = get_id_list_from_magento(params)
    params.magento_id = id_list
    if not id_list:
        return PaginatedResponse(
            params.pagination(count=0, count_pages=0),
            {},
            messages="Magento return 0 products",
        )

    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    is_customer_verified = False
    if request.user is not None and getattr(request.user, "customer", False):
        if hasattr(request.user.customer, "is_verified"):
            is_customer_verified = request.user.customer.is_verified

    products_result, count_pages, query_msg, *_ = ProductRepository().find_by_api_query(
        params=params,
        channel=channel,
        language=language,
        country=country,
        currency=currency,
        is_customer_verified=is_customer_verified,
        apply_default_order=False,
    )

    products = product_collection(products_result, asdict=True, is_customer_verified=is_customer_verified)

    if not is_customer_verified:
        messages.append("Your are not verified customer and price query may be limited")

    messages += query_msg

    return PaginatedResponse(
        params.pagination(count=len(products), count_pages=total_count),
        products,
        messages=messages,
    )
