# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_matrix.settings import OPTIONS_META_DATA

CREATED_AT_SORT = OPTIONS_META_DATA.get("order_by", {}).get("options", {}).get("created_at", {})
CREATED_AT_SORT_LABEL_LANGS = CREATED_AT_SORT.get("label", {})
CREATED_AT_SORT_POSITION = CREATED_AT_SORT.get("position", 0)


PRICE_SORT = OPTIONS_META_DATA.get("order_by", {}).get("options", {}).get("price", {})
PRICE_SORT_LABEL_LANGS = PRICE_SORT.get("label", {})
PRICE_SORT_POSITION = PRICE_SORT.get("position", 0)


PRICE_FILTER = OPTIONS_META_DATA.get("filter_by", {}).get("options", {}).get("price", {})
PRICE_FILTER_LABEL_LANGS = PRICE_FILTER.get("label", {})
PRICE_FILTER_POSITION = PRICE_FILTER.get("position", 0)


SORT_META = OPTIONS_META_DATA.get("order_by", {})
SORT_POSITION = SORT_META.get("position", 0)
SORT_LABEL_LANGS = SORT_META.get("label", {})
