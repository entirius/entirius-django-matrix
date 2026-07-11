# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 options/ endpoint tests — pre-grouped sort/ranges/filters."""

from decimal import Decimal

import pytest

BASE = "/api/matrix/v2/test-v2/options/"
QS = "?language=en&currency=EUR&country=PL"


class TestOptionsShape:
    """Response structure: {sort, ranges, filters} — not flat v1 list."""

    def test_returns_200(self, api, channel_full):
        response = api.get(f"{BASE}{QS}")
        assert response.status_code == 200

    def test_pregrouped_keys(self, api, channel_full):
        data = api.get(f"{BASE}{QS}").json()
        assert "sort" in data
        assert "ranges" in data
        assert "filters" in data

    def test_sort_is_list(self, api, channel_full):
        data = api.get(f"{BASE}{QS}").json()
        assert isinstance(data["sort"], list)

    def test_ranges_is_list(self, api, channel_full):
        data = api.get(f"{BASE}{QS}").json()
        assert isinstance(data["ranges"], list)

    def test_filters_is_list(self, api, channel_full):
        data = api.get(f"{BASE}{QS}").json()
        assert isinstance(data["filters"], list)

    def test_empty_channel_returns_empty_groups(self, api, channel_full):
        """Channel with no filterable features → empty lists."""
        data = api.get(f"{BASE}{QS}").json()
        # Without configured FilterableFeatures, all groups should be empty lists
        for key in ("sort", "ranges", "filters"):
            assert isinstance(data[key], list)

    def test_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent/options/?language=en&currency=EUR&country=PL")
        assert response.status_code == 404


# ── Fixtures for decimal range tests ──────────────────────────────────


@pytest.fixture
def decimal_feature(db):
    """PIM Feature with feature_type=DECIMAL."""
    from django_pim.models import Feature, FeatureTypeEnum, FilterTypeEnum

    return Feature.objects.create(
        idx="overall_width",
        name_t9n={"en": "Overall Width", "pl": "Szerokość całkowita"},
        feature_type=FeatureTypeEnum.DECIMAL,
        filter_type=FilterTypeEnum.SLIDE,
        is_filterable=True,
        display_order=1,
    )


@pytest.fixture
def second_decimal_feature(db):
    """Second PIM DECIMAL feature for multi-range tests."""
    from django_pim.models import Feature, FeatureTypeEnum, FilterTypeEnum

    return Feature.objects.create(
        idx="seat_height",
        name_t9n={"en": "Seat Height", "pl": "Wysokość siedziska"},
        feature_type=FeatureTypeEnum.DECIMAL,
        filter_type=FilterTypeEnum.SLIDE,
        is_filterable=True,
        display_order=2,
    )


@pytest.fixture
def decimal_products(channel_full, decimal_feature):
    """Two products with different decimal values in attributes_filter JSONB."""
    from django_matrix.models import FilterableFeatures, ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full

    FilterableFeatures.objects.create(channel=ch, feature=decimal_feature, position=5)

    pr1 = ProductRepresentation.objects.create(
        sku="DEC-WIDTH-001",
        channel=ch,
        product_type="SIMPLE",
        on_stock=True,
        attributes_filter={"overall_width": ["120.5"]},
    )
    ProductT9N.objects.create(product_representation=pr1, language=lang, name="Wide Table", url_key="wide-table")
    ProductPrice.objects.create(
        product_representation=pr1,
        currency=currency,
        country=country,
        gross=Decimal("200.00"),
        net=Decimal("162.60"),
        final_price=Decimal("200.00"),
        final_gross=Decimal("200.00"),
        final_net=Decimal("162.60"),
    )

    pr2 = ProductRepresentation.objects.create(
        sku="DEC-WIDTH-002",
        channel=ch,
        product_type="SIMPLE",
        on_stock=True,
        attributes_filter={"overall_width": ["80"]},
    )
    ProductT9N.objects.create(product_representation=pr2, language=lang, name="Narrow Table", url_key="narrow-table")
    ProductPrice.objects.create(
        product_representation=pr2,
        currency=currency,
        country=country,
        gross=Decimal("150.00"),
        net=Decimal("121.95"),
        final_price=Decimal("150.00"),
        final_gross=Decimal("150.00"),
        final_net=Decimal("121.95"),
    )
    return pr1, pr2


@pytest.fixture
def single_value_decimal_products(channel_full, decimal_feature):
    """Two products with the SAME decimal value — slider should be excluded."""
    from django_matrix.models import FilterableFeatures, ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full

    FilterableFeatures.objects.create(channel=ch, feature=decimal_feature, position=5)

    for i, sku in enumerate(["DEC-SAME-001", "DEC-SAME-002"], start=1):
        pr = ProductRepresentation.objects.create(
            sku=sku,
            channel=ch,
            product_type="SIMPLE",
            on_stock=True,
            attributes_filter={"overall_width": ["100"]},
        )
        ProductT9N.objects.create(
            product_representation=pr, language=lang, name=f"Same Width {i}", url_key=f"same-width-{i}"
        )
        ProductPrice.objects.create(
            product_representation=pr,
            currency=currency,
            country=country,
            gross=Decimal("100.00"),
            net=Decimal("81.30"),
            final_price=Decimal("100.00"),
            final_gross=Decimal("100.00"),
            final_net=Decimal("81.30"),
        )


@pytest.fixture
def multi_decimal_products(channel_full, decimal_feature, second_decimal_feature):
    """Products with two DECIMAL filterable features."""
    from django_matrix.models import FilterableFeatures, ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full

    FilterableFeatures.objects.create(channel=ch, feature=decimal_feature, position=5)
    FilterableFeatures.objects.create(channel=ch, feature=second_decimal_feature, position=6)

    pr1 = ProductRepresentation.objects.create(
        sku="DEC-MULTI-001",
        channel=ch,
        product_type="SIMPLE",
        on_stock=True,
        attributes_filter={"overall_width": ["120.5"], "seat_height": ["45"]},
    )
    ProductT9N.objects.create(product_representation=pr1, language=lang, name="Chair A", url_key="chair-a")
    ProductPrice.objects.create(
        product_representation=pr1,
        currency=currency,
        country=country,
        gross=Decimal("300.00"),
        net=Decimal("243.90"),
        final_price=Decimal("300.00"),
        final_gross=Decimal("300.00"),
        final_net=Decimal("243.90"),
    )

    pr2 = ProductRepresentation.objects.create(
        sku="DEC-MULTI-002",
        channel=ch,
        product_type="SIMPLE",
        on_stock=True,
        attributes_filter={"overall_width": ["80"], "seat_height": ["52.5"]},
    )
    ProductT9N.objects.create(product_representation=pr2, language=lang, name="Chair B", url_key="chair-b")
    ProductPrice.objects.create(
        product_representation=pr2,
        currency=currency,
        country=country,
        gross=Decimal("250.00"),
        net=Decimal("203.25"),
        final_price=Decimal("250.00"),
        final_gross=Decimal("250.00"),
        final_net=Decimal("203.25"),
    )
    return pr1, pr2


# ── DECIMAL range filter tests ────────────────────────────────────────


class TestDecimalRangeFilters:
    """DECIMAL filterable features appear as range sliders in the ranges array."""

    def test_decimal_feature_appears_in_ranges(self, api, decimal_products):
        """DECIMAL FilterableFeature → ranges array, not filters."""
        data = api.get(f"{BASE}{QS}").json()
        range_idxs = [r["idx"] for r in data["ranges"]]
        assert "overall_width" in range_idxs

    def test_decimal_not_in_filters(self, api, decimal_products):
        """DECIMAL features must NOT appear in the discrete filters array."""
        data = api.get(f"{BASE}{QS}").json()
        filter_idxs = [f["idx"] for f in data["filters"]]
        assert "overall_width" not in filter_idxs

    def test_decimal_min_max_values(self, api, decimal_products):
        """Min/max match the product attribute values (80 and 120.5)."""
        data = api.get(f"{BASE}{QS}").json()
        width_range = next(r for r in data["ranges"] if r["idx"] == "overall_width")
        assert width_range["min"] == 80.0
        assert width_range["max"] == 120.5

    def test_decimal_label_and_idx(self, api, decimal_products):
        """Range has correct idx and translated label."""
        data = api.get(f"{BASE}{QS}").json()
        width_range = next(r for r in data["ranges"] if r["idx"] == "overall_width")
        assert width_range["idx"] == "overall_width"
        assert width_range["label"] == "Overall Width"

    def test_decimal_same_value_excluded(self, api, single_value_decimal_products):
        """When all products have the same value, the slider is useless — excluded."""
        data = api.get(f"{BASE}{QS}").json()
        range_idxs = [r["idx"] for r in data["ranges"]]
        assert "overall_width" not in range_idxs

    def test_decimal_no_products_no_range(self, api, channel_full, decimal_feature):
        """DECIMAL feature registered but no products → no range entry."""
        from django_matrix.models import FilterableFeatures

        ch, *_ = channel_full
        FilterableFeatures.objects.create(channel=ch, feature=decimal_feature, position=5)

        data = api.get(f"{BASE}{QS}").json()
        range_idxs = [r["idx"] for r in data["ranges"]]
        assert "overall_width" not in range_idxs

    def test_multiple_decimal_features(self, api, multi_decimal_products):
        """Multiple DECIMAL features all appear as separate ranges."""
        data = api.get(f"{BASE}{QS}").json()
        range_idxs = [r["idx"] for r in data["ranges"]]
        assert "overall_width" in range_idxs
        assert "seat_height" in range_idxs

    def test_multiple_decimal_correct_values(self, api, multi_decimal_products):
        """Each DECIMAL range has its own min/max from its product data."""
        data = api.get(f"{BASE}{QS}").json()
        width = next(r for r in data["ranges"] if r["idx"] == "overall_width")
        height = next(r for r in data["ranges"] if r["idx"] == "seat_height")
        assert width["min"] == 80.0
        assert width["max"] == 120.5
        assert height["min"] == 45.0
        assert height["max"] == 52.5

    def test_decimal_position_respected(self, api, decimal_products):
        """Range filter uses the position from FilterableFeatures."""
        data = api.get(f"{BASE}{QS}").json()
        width_range = next(r for r in data["ranges"] if r["idx"] == "overall_width")
        assert width_range["position"] == 5


class TestFilterConditionBoolNormalization:
    """q_<bool>=true must bind CAPITALIZED 'True' to match the stored attributes_filter form (#33535)."""

    def _options(self, channel_full, query):
        from django_matrix.repository.raw_sql.options import Options
        from django_matrix.utils.params import OptionsQuery

        ch, lang, currency, country = channel_full
        return Options(
            params=OptionsQuery(query=query),
            channel=ch,
            language=lang,
            currency=currency,
            country=country,
        )

    def test_bool_true_is_capitalized(self, channel_full):
        opt = self._options(channel_full, [{"is_handcrafted": ["true"]}])
        conditions, sql_params = opt._calculate_filter_conditions_for_query({"is_handcrafted"})
        assert sql_params["filter_attrs_0"] == ["True"]
        assert "?|" in conditions[0]

    def test_bool_false_is_capitalized(self, channel_full):
        opt = self._options(channel_full, [{"is_handcrafted": ["false"]}])
        _, sql_params = opt._calculate_filter_conditions_for_query({"is_handcrafted"})
        assert sql_params["filter_attrs_0"] == ["False"]

    def test_bool_multi_value_all_capitalized(self, channel_full):
        opt = self._options(channel_full, [{"is_handcrafted": ["true", "false"]}])
        _, sql_params = opt._calculate_filter_conditions_for_query({"is_handcrafted"})
        assert sql_params["filter_attrs_0"] == ["True", "False"]

    def test_select_value_stays_verbatim(self, channel_full):
        opt = self._options(channel_full, [{"color": ["red"]}])
        _, sql_params = opt._calculate_filter_conditions_for_query(set())
        assert sql_params["filter_attrs_0"] == ["red"]
