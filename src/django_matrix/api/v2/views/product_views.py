# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Products v2 endpoints — listing, detail (via url_key), count."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from django_matrix.api.v2.mixins import ChannelMixin, known_query_params
from django_matrix.schemas.responses.common import CountResponse, PaginatedResponse
from django_matrix.services import product_service
from django_matrix.services.meta import build_meta
from django_matrix.services.product_serializer import serialize_products

# Dynamic feature filters, shared across products/, products/count/, options/, search/.
# Documented once here so the generated OpenAPI spec stays consistent (DRY).
_Q_FILTER_PARAM = OpenApiParameter(
    name="q_{feature_idx}",
    description=(
        "Value filter on a PIM feature. Replace `{feature_idx}` with the attribute idx. Repeat the param "
        "for multi-value (OR within the feature); different features are AND-combined.\n\n"
        "| Attribute type | Example | Matches |\n"
        "|---|---|---|\n"
        "| SELECT | `q_color=red` | `color` is red |\n"
        "| MULTISELECT | `q_material=wood&q_material=metal` | wood **or** metal |\n"
        "| BOOLEAN | `q_is_eco=true` | eco-flagged (`true` / `false`) |\n"
        "| DECIMAL (exact) | `q_weight_kg=5` | weight exactly 5 — use `r_` for ranges |\n\n"
        "Across features: `q_color=red&q_size=xl` → red **and** xl. "
        "TEXT and DATETIME features are not value-filterable (DATETIME is sortable via `sort`)."
    ),
)
_R_FILTER_PARAM = OpenApiParameter(
    name="r_{feature_idx}",
    description=(
        "Range filter, two values (from, to). Wired for **price**: `r_price=100&r_price=500` "
        "(canonical repeated form, `URLSearchParams`-compatible). The legacy comma form "
        "`r_price=100,500` is also accepted. Both bounds are required."
    ),
)
_S_SORT_PARAM = OpenApiParameter(
    name="s_{field}",
    description=(
        "Sort, value is the direction (`asc` / `desc`). Replace `{field}` with a system field "
        "(`price`, `name`, `created`, `sku`, `on_stock`, `relevance`) or any sortable feature idx "
        "(e.g. `weight_kg`). Consistent with the `q_` / `r_` filter prefixes.\n\n"
        "Repeat for **multi-sort** — key order is precedence: `s_price=desc&s_name=asc` → "
        "order by price DESC, then name ASC."
    ),
)
_SEARCH_PARAM = OpenApiParameter(
    name="search",
    description=(
        "Free-text query. Matches the fields the channel marks as searchable (always `sku`, plus "
        "`name` and any searchable feature configured for the channel). Combines with the `q_` / `r_` "
        "filters. On channels with full-text search enabled it also switches the default order to "
        "relevance instead of the channel default."
    ),
)
_REGIONAL_PARAMS = [
    OpenApiParameter(name="language", description="ISO 639-1 language code (defaults to channel language)"),
    OpenApiParameter(name="currency", description="ISO 4217 currency code (defaults to channel currency)"),
    OpenApiParameter(name="country", description="ISO 3166-1 country code (defaults to channel country)"),
]
_CHANNEL_PARAM = OpenApiParameter(name="channel_idx", location="path", description="Channel identifier")

# Declared once, consumed twice: by @extend_schema (documentation) and by known_query_params
# (the param.unknown warning). Neither can drift away from the other.
PRODUCTS_PARAMS = [
    _CHANNEL_PARAM,
    *_REGIONAL_PARAMS,
    OpenApiParameter(name="page", description="Page number (1-based)", type=int),
    OpenApiParameter(name="page_size", description="Results per page (default 12, max 100)", type=int),
    OpenApiParameter(name="url_key", description="Single product lookup by URL key"),
    OpenApiParameter(name="category", description="Filter by category URL key, e.g. `sofas`"),
    OpenApiParameter(name="sku", description="Batch SKU lookup. Repeat for multiple: `?sku=ABC&sku=DEF`"),
    _SEARCH_PARAM,
    _Q_FILTER_PARAM,
    _R_FILTER_PARAM,
    _S_SORT_PARAM,
    OpenApiParameter(name="product_type", description="Filter: `SIMPLE`, `CONFIGURABLE`, `BUNDLE`, `CUSTOM`"),
    OpenApiParameter(name="on_stock", description="Filter: `true` = in-stock only", type=bool),
    OpenApiParameter(
        name="include",
        description=(
            "Comma-separated response groups: `visual_assets` (swatches), `attributes` "
            "(visible attributes), `links` (product links), `full` (everything for PDP SSR)."
        ),
    ),
]

COUNT_PARAMS = [
    _CHANNEL_PARAM,
    *_REGIONAL_PARAMS,
    OpenApiParameter(name="category", description="Filter by category URL key, e.g. `sofas`"),
    OpenApiParameter(name="sku", description="Batch SKU lookup. Repeat for multiple: `?sku=ABC&sku=DEF`"),
    _SEARCH_PARAM,
    _Q_FILTER_PARAM,
    _R_FILTER_PARAM,
    OpenApiParameter(name="product_type", description="Filter: `SIMPLE`, `CONFIGURABLE`, `BUNDLE`, `CUSTOM`"),
    OpenApiParameter(name="on_stock", description="Filter: `true` = in-stock only", type=bool),
]


class ProductsView(ChannelMixin, APIView):
    """Unified products endpoint. Always returns paginated shape. Include groups control depth."""

    known_params = known_query_params(PRODUCTS_PARAMS)

    @extend_schema(
        summary="List products",
        description=(
            "Paginated product listing with public prices. Use `?url_key=` for a single product.\n\n"
            "Filter with the `q_` (value) and `r_` (range) prefixes plus `category`, `on_stock`, and "
            "`product_type` — see the parameters below. Counts for the filter sidebar come from the "
            "`options/` endpoint, which accepts the same filters.\n\n"
            "**Filter examples by attribute type:**\n"
            "- SELECT: `?q_color=red`\n"
            "- MULTISELECT (OR): `?q_material=wood&q_material=metal`\n"
            "- BOOLEAN: `?q_is_eco=true`\n"
            "- DECIMAL exact: `?q_weight_kg=5`\n"
            "- Price range: `?r_price=100&r_price=500`\n"
            "- Across features (AND): `?q_color=red&q_size=xl`\n"
            "- Combined: `?category=sofas&q_color=red&q_color=blue&r_price=100&r_price=500"
            "&s_price=asc&page=1&page_size=24`"
        ),
        parameters=PRODUCTS_PARAMS,
        responses={200: PaginatedResponse},
        tags=["Matrix Products"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)

        page = parse_page(request.query_params.get("page"))
        page_size = min(_safe_int(request.query_params.get("page_size"), 12), 100)
        include = parse_include(request.query_params.get("include", ""))

        results, has_next_page, warnings = product_service.list_products(
            channel=channel,
            language=language,
            currency=currency,
            country=country,
            page=page,
            page_size=page_size,
            category=request.query_params.get("category"),
            skus=request.query_params.getlist("sku") or None,
            url_key=request.query_params.get("url_key"),
            product_type=request.query_params.get("product_type"),
            on_stock=parse_bool(request.query_params.get("on_stock")),
            search=parse_search(request.query_params.get("search")),
            sort=parse_sort_params(request.query_params, "s_") or None,
            filters=parse_prefix_params(request.query_params, "q_") or None,
            ranges=parse_range_params(request.query_params, "r_") or None,
        )

        serialized = serialize_products(results, language, currency, country, channel, include)

        response = Response(
            {
                "has_next_page": has_next_page,
                "page": page,
                "page_size": page_size,
                "results": serialized,
                "meta": build_meta(warnings + self.get_param_warnings()),
            }
        )
        ttl = self.get_cache_ttl("products")
        if ttl > 0:
            response["Cache-Control"] = f"public, max-age=60, s-maxage={ttl}"
        return response


class ProductCountView(ChannelMixin, APIView):
    """Separate count endpoint — cached independently, longer TTL."""

    known_params = known_query_params(COUNT_PARAMS)

    @extend_schema(
        summary="Count products",
        description="Total product count matching filters. Accepts the same filter params as `products/`. Cached with a longer TTL.",
        parameters=COUNT_PARAMS,
        responses={200: CountResponse},
        tags=["Matrix Products"],
    )
    def get(self, request, channel_idx=None):
        channel = self.get_channel()
        language, currency, country = self.get_regional(channel)

        count, warnings = product_service.count_products(
            channel=channel,
            language=language,
            currency=currency,
            country=country,
            category=request.query_params.get("category"),
            skus=request.query_params.getlist("sku") or None,
            product_type=request.query_params.get("product_type"),
            on_stock=parse_bool(request.query_params.get("on_stock")),
            search=parse_search(request.query_params.get("search")),
            filters=parse_prefix_params(request.query_params, "q_") or None,
            ranges=parse_range_params(request.query_params, "r_") or None,
        )

        response = Response({"count": count, "meta": build_meta(warnings + self.get_param_warnings())})
        ttl = self.get_cache_ttl("products_count")
        if ttl > 0:
            response["Cache-Control"] = f"public, max-age=60, s-maxage={ttl}"
        return response


# ── HTTP param parsers (view-layer concern) ─────────────────────────


def parse_prefix_params(query_params, prefix: str) -> dict:
    """Parse q_color=red&q_color=blue → {'color': ['red', 'blue']}."""
    result = {}
    for key in query_params:
        if key.startswith(prefix):
            feature_idx = key[len(prefix) :]
            values = query_params.getlist(key)
            if feature_idx and values:
                result[feature_idx] = values
    return result


def parse_range_params(query_params, prefix: str) -> dict:
    """Parse range filter params. Accepts two formats:

    - repeated params:  r_price=100&r_price=500 → {'price': ['100', '500']}
    - comma-separated:  r_price=100,500          → {'price': ['100', '500']}

    Silently skips malformed entries (wrong arity, empty feature_idx).
    """
    result = {}
    seen = set()
    for key in query_params:
        if not key.startswith(prefix) or key in seen:
            continue
        seen.add(key)
        feature_idx = key[len(prefix) :]
        if not feature_idx:
            continue

        values = query_params.getlist(key)
        if len(values) == 2:
            result[feature_idx] = values
        elif len(values) == 1 and "," in values[0]:
            parts = values[0].split(",")
            if len(parts) == 2:
                result[feature_idx] = parts
    return result


def parse_sort_params(query_params, prefix: str) -> list[dict]:
    """Parse s_price=desc&s_name=asc → [{'price': 'DESC'}, {'name': 'ASC'}].

    URL order is sort precedence (first key = primary). Direction is upper-cased;
    invalid directions are normalised to ASC downstream (repository get_asc_desc).
    """
    result = []
    for key in query_params:
        if key.startswith(prefix):
            field = key[len(prefix) :]
            if field:
                result.append({field: (query_params.get(key) or "ASC").upper()})
    return result


def parse_search(value: str | None) -> str | None:
    """Blank and whitespace-only queries mean 'no search', not `ILIKE '% %'`."""
    return (value or "").strip() or None


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes")


def _safe_int(value, default: int) -> int:
    """Parse int from query param, returning default on invalid input."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_page(value) -> int:
    """1-based page number. `?page=0` and negatives would produce a negative SQL OFFSET (HTTP 500)."""
    return max(_safe_int(value, 1), 1)


def parse_include(include_str: str) -> set[str]:
    """Parse include=visual_assets,attributes → {'visual_assets', 'attributes'}."""
    if not include_str:
        return set()
    groups = {g.strip() for g in include_str.split(",")}
    if "full" in groups:
        groups.update({"visual_assets", "attributes", "seo", "content", "related", "links"})
    return groups
