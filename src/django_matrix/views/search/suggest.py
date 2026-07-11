# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from base64 import b64encode

from django_utils.api.decorators import api_view, authenticate_optional, parse_parameters, require_http_method
from django_utils.api.exceptions import BadRequest
from django_utils.api.responses import PaginatedResponse
from magento2_sdk2.dto.search import SearchResult, SuggestParameters
from magento2_sdk2.services.client import Magento2Client
from magento2_sdk2.services.worker import suggest

from django_matrix.dto.view.product import product_collection
from django_matrix.repository.raw_sql.product import Product as ProductRepository
from django_matrix.settings import MAGENTO_BASIC_AUTH_LOGIN, MAGENTO_BASIC_AUTH_PASSWORD, MAGENTO_TOKEN, MAGENTO_URL
from django_matrix.utils.decorators import prepare_view
from django_matrix.utils.params import MagentoQuery, get_view_variable_from_kwargs

logger_process = logging.getLogger("process")


def get_suggest_term_and_products_id(params):
    """
    Function with params which use magento2_sdk2 and endpoint suggest to get suggest_data return it.
    """
    if not MAGENTO_URL or not MAGENTO_TOKEN:
        raise BadRequest("Configure Magento settings")
    if not params.search_text:
        raise BadRequest("Need to specify search_text")

    credentials_b64 = b64encode(f"{MAGENTO_BASIC_AUTH_LOGIN}:{MAGENTO_BASIC_AUTH_PASSWORD}".encode()).decode()

    magento_client: Magento2Client = Magento2Client(
        base_url=MAGENTO_URL, access_token=credentials_b64, access_type="Basic"
    )

    text_search = params.search_text

    search_params_obj = SuggestParameters(q=str(text_search))
    suggest_results = []
    try:
        response = suggest(magento_client, search_params_obj)
        suggest_data = {"sku": [], "term": []}
        for each in response:
            suggest_results = SearchResult.Schema().load(each)
            suggest_data = suggest_results.get_only_important_data(suggest_data=suggest_data, text_search=text_search)
    except Exception as e:
        logger_process.error(f"{e}", extra={"details": {"params": params}})
        raise BadRequest("Magento error. Check process log file")

    return suggest_data


@api_view
@authenticate_optional
@require_http_method("GET")
@parse_parameters(MagentoQuery.Schema())
@prepare_view
def suggest_listing_view(request, params: MagentoQuery, *args, **kwargs) -> "PaginatedResponse":
    """Returns a paginated response with a list of products and suggestion"""

    if not params.search_text:
        raise BadRequest("Need to specify search_text")
    try:
        suggest_data = get_suggest_term_and_products_id(params)
    except Exception as e:
        logger_process.error(f"{e}", extra={"details": {"params": params}})
        raise BadRequest("Magento error. Check process log file")

    if not suggest_data["sku"]:
        return PaginatedResponse(params.pagination(count=0, count_pages=0), {}, messages="Magento return 0 products")
    else:
        params.sku = suggest_data["sku"]

    language, currency, country, channel, messages = get_view_variable_from_kwargs(kwargs)
    is_customer_verified = (
        request.user.customer.is_verified
        if (request.user is not None and getattr(request.user, "is_customer", False))
        else False
    )

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
    products = suggest_data["term"] + products
    if not is_customer_verified:
        messages.append("Your are not verified customer and price query may be limited")

    messages += query_msg

    return PaginatedResponse(
        params.pagination(count=len(products), count_pages=count_pages), products, messages=messages
    )
