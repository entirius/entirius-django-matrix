# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Product serialization — converts raw SQL results to v2 response shape.

Extracted from views per rule: 'No _build_* / _serialize_* helpers in view files.'
"""

import json


def serialize_products(results: list[dict], language, currency, country, channel, include: set[str]) -> list[dict]:
    """Serialize a page of products. Batch-fetches attributes, url_keys, children, category paths to avoid N+1."""
    lang_iso = language.iso2 if language else "en"
    currency_code = (
        currency.iso3 if currency else (channel.default_currency.iso3 if channel.default_currency else "EUR")
    )

    skus = [r.get("sku") for r in results if r.get("sku")]

    # Batch-fetch attributes for all SKUs (one query per group, not per product)
    attrs_cache = (
        _prefetch_attributes(skus, channel, include) if include & {"visual_assets", "attributes", "seo", "full"} else {}
    )

    # Batch-fetch url_keys for SEO hreflang (one query, not one per product)
    url_keys_cache = _prefetch_url_keys(skus, channel) if include & {"seo", "full"} else {}

    # Batch-fetch configurable children SKUs (one query, not one per product)
    children_cache = _prefetch_configurable_children(skus, channel) if include & {"related", "full"} else {}

    # Batch-fetch category breadcrumb paths (one query for all categories)
    cat_path_cache: dict[str, list[dict]] = {}
    if "full" in include:
        all_cat_idxs = set()
        for r in results:
            for cat in _parse_json(r.get("categories_data")) or []:
                if cat.get("idx"):
                    all_cat_idxs.add(cat["idx"])
        if all_cat_idxs:
            cat_path_cache = _prefetch_category_paths(all_cat_idxs, channel, lang_iso)

    return [
        _serialize_product(
            r, lang_iso, currency_code, channel, include, attrs_cache, url_keys_cache, children_cache, cat_path_cache
        )
        for r in results
    ]


def _prefetch_attributes(skus: list[str], channel, include: set[str]) -> dict[str, dict[str, list[dict]]]:
    """Batch-fetch attributes for all SKUs in one query per include group. Returns {sku: {group: [attrs]}}."""
    from django_matrix.models import Attribute

    result: dict[str, dict[str, list[dict]]] = {}
    groups_to_fetch = []

    if "visual_assets" in include or "full" in include:
        groups_to_fetch.append(("visual_assets", {"has_visual_asset": True}))
    if "attributes" in include or "full" in include:
        groups_to_fetch.append(("attributes", {"is_visible": True}))
    if "seo" in include or "full" in include:
        groups_to_fetch.append(("seo", {"is_seo": True}))

    for group_name, flag_filter in groups_to_fetch:
        qs = (
            Attribute.objects.filter(product__sku__in=skus, product__channel=channel, **flag_filter)
            .select_related("product")
            .values(
                "product__sku",
                "feature_idx",
                "feature_name_t9n",
                "feature_type",
                "attribute_idx",
                "attribute_value_text",
                "attribute_value_t9n",
                "attribute_value_json",
                "extension",
                "is_visible",
                "has_visual_asset",
                "is_comparable",
                "is_seo",
                "linking",
                "group_idx",
                "group_name_t9n",
                "group_position",
            )
        )
        for attr in qs:
            sku = attr.pop("product__sku")
            result.setdefault(sku, {}).setdefault(group_name, []).append(attr)

    return result


def _serialize_product(
    raw: dict,
    lang_iso: str,
    currency_code: str,
    channel,
    include: set[str],
    attrs_cache: dict,
    url_keys_cache: dict,
    children_cache: dict,
    cat_path_cache: dict,
) -> dict:
    """Serialize raw SQL result to v2 response shape."""
    sku = raw.get("sku", "")

    product = {
        "sku": sku,
        "product_type": raw.get("product_type", "SIMPLE"),
        "is_virtual": raw.get("is_virtual", False)
        if "is_virtual" in raw
        else (raw.get("kind_of_product") == "VIRTUAL"),
        "url_key": raw.get("url_key", ""),
        "name": raw.get("name", sku),
        "main_image": _parse_json(raw.get("main_image")),
        "badges": _parse_json(raw.get("badges")),
        "subnames": _parse_json(raw.get("subnames")),
        "brands": _parse_json(raw.get("brands")),
        "feature_set": _parse_json(raw.get("feature_set")),
        "on_stock": raw.get("on_stock"),
        "parent_sku": raw.get("parent_sku"),
        "parent_url_key": raw.get("parent_url_key"),
        "review_rating": str(raw["average_rating"]) if raw.get("average_rating") else None,
        "review_count": raw.get("number_of_reviews"),
        "price": _build_price(raw, currency_code),
        "categories": _parse_json(raw.get("categories_data")) or [],
    }

    sku_attrs = attrs_cache.get(sku, {})

    if "visual_assets" in include or "full" in include:
        product["visual_assets"] = [_serialize_attribute(a, lang_iso) for a in sku_attrs.get("visual_assets", [])]

    if "attributes" in include or "full" in include:
        product["attributes"] = [_serialize_attribute(a, lang_iso) for a in sku_attrs.get("attributes", [])]

    if "seo" in include or "full" in include:
        # Decision #20: url_keys dict {lang: url_key} for hreflang SEO
        product["url_keys"] = url_keys_cache.get(sku, {})
        product["meta_title"] = raw.get("meta_title")
        product["meta_description"] = raw.get("meta_description")
        product["seo_attributes"] = [
            {"feature_idx": a["feature_idx"], "value": _resolve_attr_value(a, lang_iso)}
            for a in sku_attrs.get("seo", [])
        ]

    # Decision #35: extend categories with path (breadcrumbs) when full
    if "full" in include and product["categories"]:
        product["categories"] = [
            {**cat_data, "path": cat_path_cache.get(cat_data.get("idx"), [])} if cat_data.get("idx") else cat_data
            for cat_data in product["categories"]
        ]

    if "content" in include or "full" in include:
        product["description"] = raw.get("desc")
        product["short_description"] = raw.get("short_desc")
        product["media"] = _build_media(raw)
        product["attachments"] = _build_attachments(raw, lang_iso)

    if "related" in include or "full" in include:
        product["offer"] = None
        product["variant_options"] = []
        product["variants"] = []
        product["bundle_config"] = None
        # children: bundle uses JSON field, configurable uses parent FK
        children_json = _parse_json(raw.get("children")) or []
        if not children_json and raw.get("product_type") == "CONFIGURABLE":
            children_json = children_cache.get(sku, [])
        product["children_skus"] = children_json

    if "links" in include or "full" in include:
        product["product_links"] = _parse_json(raw.get("product_links")) or []

    return product


def _build_price(raw: dict, currency_code: str) -> dict | None:
    """Build v2 price object from raw SQL row."""
    if raw.get("final_price") is None and raw.get("range_from") is None and raw.get("final_gross") is None:
        return None

    return {
        "currency": currency_code,
        "tax_rate": str(raw["tax_amount"]) if raw.get("tax_amount") else None,
        "is_range": bool(raw.get("is_range", False)),
        "gross": _dec(raw.get("gross")) or _dec(raw.get("price")),
        "net": _dec(raw.get("net")) or _dec(raw.get("price_tax_config_opposite")),
        "final_gross": _dec(raw.get("final_gross")) or _dec(raw.get("final_price")),
        "final_net": _dec(raw.get("final_net")),
        "has_special_price": bool(raw.get("has_special_price", False)),
        "special_gross": _dec(raw.get("special_gross")) or _dec(raw.get("special_price")),
        "special_net": _dec(raw.get("special_net")),
        "percent_off": raw.get("percent_off"),
        "special_from_date": raw.get("special_from_date"),
        "special_to_date": raw.get("special_to_date"),
        "range_from_gross": _dec(raw.get("range_from")),
        "range_from_net": _dec(raw.get("range_from_net")),
        "range_to_gross": _dec(raw.get("range_to")),
        "range_to_net": _dec(raw.get("range_to_net")),
        "range_from_special_gross": _dec(raw.get("special_price_range_from")),
        "range_from_special_net": _dec(raw.get("range_from_special_net")),
        "range_to_special_gross": _dec(raw.get("special_price_range_to")),
        "range_to_special_net": _dec(raw.get("range_to_special_net")),
    }


def _parse_json(value):
    """Parse JSON string to dict/list if needed."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _dec(value) -> str | None:
    if value is None:
        return None
    return str(value)


BOOL_LABELS = {
    "True": {"en": "Yes", "pl": "Tak", "de": "Ja", "fr": "Oui"},
    "False": {"en": "No", "pl": "Nie", "de": "Nein", "fr": "Non"},
}


def _serialize_attribute(attr: dict, lang_iso: str) -> dict:
    value = _resolve_attr_value(attr, lang_iso)
    value_idx = attr.get("attribute_idx")

    # BOOL: value = translated display ("Yes"/"Tak"), value_idx = "true"/"false"
    if attr.get("feature_type") == "BOOL" and value in ("True", "False"):
        value_idx = value.lower()  # "true" / "false"
        value = BOOL_LABELS.get(value, {}).get(lang_iso, value)

    return {
        "feature_idx": attr["feature_idx"],
        "feature_name": attr["feature_name_t9n"].get(lang_iso, "") if attr.get("feature_name_t9n") else "",
        "feature_type": attr["feature_type"],
        "value": value,
        "value_idx": value_idx,
        "is_visible": attr.get("is_visible", True),
        "has_visual_asset": attr.get("has_visual_asset", False),
        "is_comparable": attr.get("is_comparable", False),
        "extension": attr.get("extension"),
        "group_idx": attr.get("group_idx"),
        "group_name": attr["group_name_t9n"].get(lang_iso, "") if attr.get("group_name_t9n") else None,
        "group_position": attr.get("group_position"),
    }


def _resolve_attr_value(attr: dict, lang_iso: str) -> str | None:
    if attr.get("attribute_value_text"):
        return attr["attribute_value_text"]
    if attr.get("attribute_value_t9n"):
        t9n = attr["attribute_value_t9n"]
        return t9n.get(lang_iso) or next(iter(t9n.values()), None) if isinstance(t9n, dict) else str(t9n)
    if attr.get("attribute_value_json"):
        return str(attr["attribute_value_json"])
    return None


def _prefetch_url_keys(skus: list[str], channel) -> dict[str, dict[str, str]]:
    """Batch-fetch {sku: {lang_iso: url_key}} for all SKUs in one query."""
    from django_matrix.models import ProductT9N

    t9ns = ProductT9N.objects.filter(
        product_representation__sku__in=skus,
        product_representation__channel=channel,
        url_key__isnull=False,
    ).values_list("product_representation__sku", "language__iso2", "url_key")

    result: dict[str, dict[str, str]] = {}
    for sku, lang, url_key in t9ns:
        if lang and url_key:
            result.setdefault(sku, {})[lang] = url_key
    return result


def _prefetch_configurable_children(skus: list[str], channel) -> dict[str, list[str]]:
    """Batch-fetch {parent_sku: [child_skus]} for configurable products in one query."""
    from django_matrix.models import ProductRepresentation

    children = ProductRepresentation.objects.filter(
        parent__sku__in=skus, parent__channel=channel, channel=channel
    ).values_list("parent__sku", "sku")

    result: dict[str, list[str]] = {}
    for parent_sku, child_sku in children:
        result.setdefault(parent_sku, []).append(child_sku)
    return result


def _prefetch_category_paths(cat_idxs: set[str], channel, lang_iso: str) -> dict[str, list[dict]]:
    """Batch-fetch category breadcrumb paths. Loads all channel categories once, resolves parent chains in Python."""
    try:
        from django_pim.models import ProductCategory
    except ImportError:
        return {}

    all_cats = list(ProductCategory.objects.filter(shop__idx=channel.idx))
    cat_by_idx = {c.idx: c for c in all_cats}
    cat_by_pk = {c.pk: c for c in all_cats}

    result: dict[str, list[dict]] = {}
    for cat_idx in cat_idxs:
        cat = cat_by_idx.get(cat_idx)
        if not cat:
            continue
        path = []
        current = cat
        while current:
            if current.parent_category_id is not None:
                path.append(
                    {
                        "name": current.name_lang(lang_iso) if hasattr(current, "name_lang") else current.idx,
                        "url_key": current.url_key_t9n.get(lang_iso, current.idx),
                    }
                )
            current = cat_by_pk.get(current.parent_category_id)
        path.reverse()
        result[cat_idx] = path
    return result


def _build_media(raw: dict) -> list:
    pictures = _parse_json(raw.get("pictures")) or []
    videos = _parse_json(raw.get("videos")) or []
    media = []
    for pic in pictures if isinstance(pictures, list) else []:
        media.append({**pic, "type": "image"})
    for vid in videos if isinstance(videos, list) else []:
        item = {**vid, "type": "video"}
        source_set = vid.get("source_set") or []
        if source_set and isinstance(source_set, list):
            item["video_source"] = _normalize_video_source(source_set[0].get("source", ""))
        else:
            item["video_source"] = "unknown"
        media.append(item)
    media.sort(key=lambda x: x.get("position", 9999))
    return media


_VIDEO_SOURCE_MAP = {"youtube": "youtube", "vimeo": "vimeo", "unknown": "unknown"}


def _normalize_video_source(raw: str) -> str:
    """Normalize video source label to API-standard lowercase identifier."""
    return _VIDEO_SOURCE_MAP.get(raw.lower(), "unknown") if raw else "unknown"


def _build_attachments(raw: dict, lang_iso: str) -> list:
    """Build attachment list with resolved labels for current language."""
    attachments = _parse_json(raw.get("attachments")) or []
    if not isinstance(attachments, list):
        return []
    result = []
    for att in attachments:
        label_t9n = att.get("file_label_t9n") or {}
        cat_name_t9n = att.get("category_name_t9n") or {}
        result.append(
            {
                "file_label": label_t9n.get(lang_iso) or att.get("file_label") or att.get("original_file_name"),
                "original_file_name": att.get("original_file_name"),
                "file_path": att.get("file_path"),
                "file_type": att.get("file_type", "undefined"),
                "file_size": att.get("file_size"),
                "category_code": att.get("category_code"),
                "category_name": cat_name_t9n.get(lang_iso) or att.get("category_code"),
            }
        )
    return result
