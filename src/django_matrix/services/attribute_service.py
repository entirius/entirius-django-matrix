# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_matrix.dto.view.attribute import attribute_collection
from django_matrix.repository.raw_sql.attribute import Attribute as AttributeRepository
from django_matrix.utils.params import AttributeQuery


def fetch_and_attach_attributes(
    items: list[dict],
    *,
    channel,
    language,
    sku_field: str = "sku",
    use_full_data_features: bool = False,
) -> list[str]:
    """Fetches attributes for the given items and mutates each with an ``attributes`` list.

    Same logic the listing endpoint uses for ``fetch_attributes=true`` — extracted so
    bundle-config and other endpoints can opt in without duplicating the fetch+collect+attach
    triplet. Items must be dicts containing ``sku_field`` (default: ``"sku"``).

    Returns the message list produced by the attribute repository.
    """
    if not items:
        return []
    sku_list = [item[sku_field] for item in items if item.get(sku_field)]
    if not sku_list:
        return []

    attr_params = AttributeQuery(sku=sku_list)
    attributes_result, attr_msg = AttributeRepository().find_by_api_query(
        params=attr_params,
        channel=channel,
        language=language,
        use_full_data_features=use_full_data_features,
    )
    attributes_by_sku = attribute_collection(attributes_result, asdict=True, language_iso2=language.iso2)

    for item in items:
        sku = item.get(sku_field)
        if sku and sku in attributes_by_sku:
            item["attributes"] = attributes_by_sku[sku]
    return attr_msg
