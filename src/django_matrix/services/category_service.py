# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Category service — builds nested tree from PIM categories."""

import operator
from functools import reduce

from django.db.models import Q


def get_category_tree(
    channel, language, depth: int | None = None, parent_url_keys: list[str] | None = None
) -> list[dict]:
    """Returns nested category tree. Only is_active=True and is_in_menu=True.

    parent_url_keys: scope the tree to the children of those parents (subtrees
    merged, deduped). None → full tree from the real roots. `depth` limits levels
    counted from the response top (depth=1 → one level / lazy).
    """
    try:
        from django_pim.models import ProductCategory
    except ImportError:
        return []

    lang_iso = language.iso2 if language else "en"

    categories = list(
        ProductCategory.objects.filter(shop__idx=channel.idx, is_active=True, is_in_menu=True)
        .order_by("position")
        .select_related("parent_category")
    )
    return _build_tree(categories, lang_iso, depth, parent_url_keys)


def get_single_category(channel, language, url_key: str) -> dict | None:
    """Returns single category with SEO fields. Ignores is_in_menu (direct lookup)."""
    try:
        from django_pim.models import ProductCategory
    except ImportError:
        return None

    lang_iso = language.iso2 if language else "en"

    cat = (
        ProductCategory.objects.filter(shop__idx=channel.idx, is_active=True, **{f"url_key_t9n__{lang_iso}": url_key})
        .select_related("parent_category__parent_category__parent_category__parent_category")
        .first()
    )

    if not cat:
        return None

    return _single_category_dict(channel, cat, lang_iso)


def get_categories(channel, language, url_keys: list[str]) -> list[dict]:
    """Batch single-category lookup. Order follows url_keys; missing skipped; deduped.

    One query via OR of exact url_key matches (not __in on the JSON key transform).
    """
    try:
        from django_pim.models import ProductCategory
    except ImportError:
        return []

    lang_iso = language.iso2 if language else "en"

    unique_keys = list(dict.fromkeys(url_keys))
    if not unique_keys:
        return []

    match = reduce(operator.or_, (Q(**{f"url_key_t9n__{lang_iso}": k}) for k in unique_keys))
    cats = (
        ProductCategory.objects.filter(shop__idx=channel.idx, is_active=True)
        .filter(match)
        .select_related("parent_category__parent_category__parent_category__parent_category")
    )
    by_key = {cat.url_key_t9n.get(lang_iso): cat for cat in cats}
    return [_single_category_dict(channel, by_key[k], lang_iso) for k in unique_keys if k in by_key]


def _single_category_dict(channel, cat, lang_iso: str) -> dict:
    """Build the full SEO category dict (shared by single + batch lookups)."""
    from django_pim.models import ProductCategory

    children = list(
        ProductCategory.objects.filter(shop__idx=channel.idx, parent_category=cat, is_active=True).order_by("position")
    )

    return {
        "idx": cat.idx,
        "name": cat.name_lang(lang_iso),
        "url_key": cat.url_key_t9n.get(lang_iso, cat.idx),
        "url_keys": {k: v for k, v in cat.url_key_t9n.items() if v},
        "description": cat.description_lang(lang_iso),
        "image_url": cat.image_url or None,
        "og_image_url": cat.og_image_url or None,
        "meta_title": cat.meta_title_t9n.get(lang_iso),
        "meta_description": cat.meta_description_t9n.get(lang_iso),
        "canonical_url": cat.canonical_url_t9n.get(lang_iso),
        "noindex": cat.noindex,
        "nofollow": cat.nofollow,
        "rich_content": cat.rich_content,
        "position": cat.position,
        "products_count": _count_products_in_category(channel, cat),
        "has_children": bool(children),
        "breadcrumbs": _build_breadcrumbs(cat, lang_iso),
        "children": [_category_to_dict(c, lang_iso, include_children=False) for c in children],
    }


def _build_tree(
    categories, lang_iso: str, max_depth: int | None = None, parent_url_keys: list[str] | None = None
) -> list[dict]:
    """Build nested tree from flat category list, optionally rooted at given parents."""
    by_parent = {}
    roots = []

    for cat in categories:
        parent_id = cat.parent_category_id
        if parent_id is None:
            roots.append(cat)
        else:
            by_parent.setdefault(parent_id, []).append(cat)

    def _recurse(cat, current_depth):
        if max_depth and current_depth > max_depth:
            return None
        children = []
        for child in by_parent.get(cat.pk, []):
            node = _recurse(child, current_depth + 1)
            if node:
                children.append(node)
        result = _category_to_dict(cat, lang_iso, include_children=True)
        result["children"] = children
        result["has_children"] = bool(by_parent.get(cat.pk))
        return result

    if parent_url_keys is not None:
        top = _subtree_roots(categories, by_parent, lang_iso, parent_url_keys)
    else:
        top = roots

    result = []
    for r in top:
        node = _recurse(r, 1)
        if node:
            result.append(node)

    # Single root → skip it, promote its children to top level (full tree only).
    # Root categories are organizational, not navigational.
    if parent_url_keys is None and len(result) == 1:
        return result[0].get("children", [])
    return result


def _subtree_roots(categories, by_parent: dict, lang_iso: str, parent_url_keys: list[str]) -> list:
    """Direct children of the requested parents, request order, deduped."""
    by_url = {}
    for cat in categories:
        key = cat.url_key_t9n.get(lang_iso)
        if key:
            by_url.setdefault(key, cat)

    seen = set()
    roots = []
    for parent_key in parent_url_keys:
        parent = by_url.get(parent_key)
        if not parent:
            continue
        for child in by_parent.get(parent.pk, []):
            if child.pk not in seen:
                seen.add(child.pk)
                roots.append(child)
    return roots


def _category_to_dict(cat, lang_iso: str, include_children: bool = False) -> dict:
    result = {
        "idx": cat.idx,
        "name": cat.name_lang(lang_iso),
        "url_key": cat.url_key_t9n.get(lang_iso, cat.idx),
        "url_keys": {k: v for k, v in cat.url_key_t9n.items() if v},
        "description": cat.description_lang(lang_iso) if hasattr(cat, "description_lang") else None,
        "image_url": cat.image_url or None,
        "position": cat.position,
        "products_count": 0,
    }
    if include_children:
        result["children"] = []
    return result


def _build_breadcrumbs(cat, lang_iso: str) -> list[dict]:
    """Build breadcrumb path from leaf to root."""
    path = []
    current = cat
    while current:
        if current.parent_category is not None:
            path.append(
                {"name": current.name_lang(lang_iso), "url_key": current.url_key_t9n.get(lang_iso, current.idx)}
            )
        current = current.parent_category
    path.reverse()
    return path


def _count_products_in_category(channel, cat) -> int:
    try:
        from django_matrix.models import ProductRepresentation
    except ImportError:
        return 0

    url_key = list(cat.url_key_t9n.values())[0] if cat.url_key_t9n else cat.idx
    return ProductRepresentation.objects.filter(
        channel__idx=channel.idx, categories_url_key__contains=[url_key]
    ).count()
