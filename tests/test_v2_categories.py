# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 categories/ endpoint tests — tree, depth, single with SEO, is_in_menu, url_keys."""

import pytest

BASE = "/api/matrix/v2/test-v2/categories/"


@pytest.fixture
def pim_category(channel_full):
    """PIM ProductCategory tree: root + child with multi-language url_key_t9n."""
    try:
        from django_pim.models import Channel as PimChannel
        from django_pim.models import ProductCategory
    except ImportError:
        pytest.skip("django_pim not available")

    ch, lang, currency, country = channel_full
    pim_ch, _ = PimChannel.objects.get_or_create(
        idx="test-v2", defaults={"name": "Test v2 PIM", "default_language": lang, "default_currency": currency}
    )
    root = ProductCategory.objects.create(
        shop=pim_ch,
        idx="root",
        url_key_t9n={"en": "root"},
        name_t9n={"en": "Root"},
        is_active=True,
        is_in_menu=True,
        tree_deep=0,
        position=1,
    )
    cat = ProductCategory.objects.create(
        shop=pim_ch,
        idx="electronics",
        url_key_t9n={"en": "electronics", "pl": "elektronika"},
        name_t9n={"en": "Electronics", "pl": "Elektronika"},
        parent_category=root,
        is_active=True,
        is_in_menu=True,
        tree_deep=1,
        position=1,
    )
    return cat


@pytest.fixture
def pim_tree(channel_full):
    """Deeper PIM tree for batch / parent_url_key / has_children tests.

    root → {sofas → [living-room-sofas, sofa-beds], chairs → [office-chairs]}
    Single root is promoted away, so the tree top level is [sofas, chairs].
    """
    try:
        from django_pim.models import Channel as PimChannel
        from django_pim.models import ProductCategory
    except ImportError:
        pytest.skip("django_pim not available")

    ch, lang, currency, country = channel_full
    pim_ch, _ = PimChannel.objects.get_or_create(
        idx="test-v2", defaults={"name": "Test v2 PIM", "default_language": lang, "default_currency": currency}
    )

    def _cat(idx, url_key, parent, pos, deep):
        return ProductCategory.objects.create(
            shop=pim_ch,
            idx=idx,
            url_key_t9n={"en": url_key},
            name_t9n={"en": idx.replace("-", " ").title()},
            parent_category=parent,
            is_active=True,
            is_in_menu=True,
            tree_deep=deep,
            position=pos,
        )

    root = _cat("root", "root", None, 1, 0)
    sofas = _cat("sofas", "sofas", root, 1, 1)
    _cat("living-room-sofas", "living-room-sofas", sofas, 1, 2)
    _cat("sofa-beds", "sofa-beds", sofas, 2, 2)
    chairs = _cat("chairs", "chairs", root, 2, 1)
    _cat("office-chairs", "office-chairs", chairs, 1, 2)
    return pim_ch


class TestCategoriesTree:
    """Default tree response."""

    def test_returns_200(self, api, channel_full):
        response = api.get(f"{BASE}?language=en")
        assert response.status_code == 200

    def test_returns_list(self, api, channel_full):
        """Default tree is a list (not wrapped in results)."""
        data = api.get(f"{BASE}?language=en").json()
        assert isinstance(data, list)

    def test_empty_channel_returns_empty_list(self, api, channel_full):
        """Channel with no PIM categories → empty list."""
        data = api.get(f"{BASE}?language=en").json()
        assert isinstance(data, list)


class TestCategoriesSingle:
    """Single category lookup via ?url_key=."""

    def test_single_wraps_in_results(self, api, channel_full):
        response = api.get(f"{BASE}?language=en&url_key=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_nonexistent_url_key_empty_results(self, api, channel_full):
        data = api.get(f"{BASE}?language=en&url_key=nonexistent").json()
        assert data["results"] == []


class TestCategoriesParams:
    """Query parameter handling."""

    def test_depth_param_accepted(self, api, channel_full):
        response = api.get(f"{BASE}?language=en&depth=1")
        assert response.status_code == 200

    def test_parent_url_key_param_accepted(self, api, channel_full):
        response = api.get(f"{BASE}?language=en&parent_url_key=furniture")
        assert response.status_code == 200

    def test_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent/categories/?language=en")
        assert response.status_code == 404


class TestCategoryUrlKeys:
    """url_keys dict for hreflang SEO."""

    def test_tree_includes_url_keys(self, api, pim_category):
        data = api.get(f"{BASE}?language=en").json()
        assert len(data) >= 1
        assert "url_keys" in data[0]
        assert isinstance(data[0]["url_keys"], dict)

    def test_single_includes_url_keys(self, api, pim_category):
        data = api.get(f"{BASE}?language=en&url_key=electronics").json()
        assert len(data["results"]) == 1
        assert "url_keys" in data["results"][0]

    def test_url_keys_has_correct_values(self, api, pim_category):
        data = api.get(f"{BASE}?language=en&url_key=electronics").json()
        url_keys = data["results"][0]["url_keys"]
        assert url_keys == {"en": "electronics", "pl": "elektronika"}

    def test_url_keys_excludes_empty_values(self, api, channel_full):
        """Empty string values in url_key_t9n are filtered out."""
        try:
            from django_pim.models import Channel as PimChannel
            from django_pim.models import ProductCategory
        except ImportError:
            pytest.skip("django_pim not available")

        ch, lang, currency, country = channel_full
        pim_ch, _ = PimChannel.objects.get_or_create(
            idx="test-v2", defaults={"name": "Test v2 PIM", "default_language": lang, "default_currency": currency}
        )
        ProductCategory.objects.create(
            shop=pim_ch,
            idx="sparse-cat",
            url_key_t9n={"en": "sparse", "de": ""},
            name_t9n={"en": "Sparse"},
            is_active=True,
            is_in_menu=True,
            tree_deep=0,
            position=2,
        )
        data = api.get(f"{BASE}?language=en&url_key=sparse").json()
        url_keys = data["results"][0]["url_keys"]
        assert url_keys == {"en": "sparse"}
        assert "de" not in url_keys


class TestCategoriesBatch:
    """Batch lookup: ?url_key=a&url_key=b → {results: [...]}."""

    def test_batch_returns_both(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&url_key=sofas&url_key=chairs").json()
        keys = [c["url_key"] for c in data["results"]]
        assert keys == ["sofas", "chairs"]

    def test_batch_preserves_request_order(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&url_key=chairs&url_key=sofas").json()
        keys = [c["url_key"] for c in data["results"]]
        assert keys == ["chairs", "sofas"]

    def test_batch_skips_missing(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&url_key=sofas&url_key=ghost&url_key=chairs").json()
        keys = [c["url_key"] for c in data["results"]]
        assert keys == ["sofas", "chairs"]

    def test_single_value_unchanged(self, api, pim_tree):
        """Backward compat: one url_key still wraps a single result."""
        data = api.get(f"{BASE}?language=en&url_key=sofas").json()
        assert len(data["results"]) == 1
        assert data["results"][0]["url_key"] == "sofas"

    def test_too_many_url_keys_returns_400(self, api, channel_full):
        query = "&".join(f"url_key=c{i}" for i in range(51))
        response = api.get(f"{BASE}?language=en&{query}")
        assert response.status_code == 400


class TestCategoriesParentSubtree:
    """parent_url_key: fixed subtree scoping + lazy depth."""

    def test_parent_returns_direct_children(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&parent_url_key=sofas").json()
        keys = sorted(c["url_key"] for c in data)
        assert keys == ["living-room-sofas", "sofa-beds"]

    def test_parent_with_depth_one_is_one_level(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&parent_url_key=sofas&depth=1").json()
        keys = sorted(c["url_key"] for c in data)
        assert keys == ["living-room-sofas", "sofa-beds"]
        assert all(c["children"] == [] for c in data)

    def test_multiple_parents_merged(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&parent_url_key=sofas&parent_url_key=chairs").json()
        keys = sorted(c["url_key"] for c in data)
        assert keys == ["living-room-sofas", "office-chairs", "sofa-beds"]

    def test_unknown_parent_returns_empty(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&parent_url_key=ghost").json()
        assert data == []


class TestCategoriesHasChildren:
    """has_children flag on every node."""

    def test_tree_node_with_children_true(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en").json()
        sofas = next(c for c in data if c["url_key"] == "sofas")
        assert sofas["has_children"] is True

    def test_leaf_node_false(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en").json()
        sofas = next(c for c in data if c["url_key"] == "sofas")
        leaf = next(c for c in sofas["children"] if c["url_key"] == "sofa-beds")
        assert leaf["has_children"] is False

    def test_present_in_subtree_response(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&parent_url_key=sofas").json()
        assert all("has_children" in c for c in data)

    def test_present_in_single_lookup(self, api, pim_tree):
        data = api.get(f"{BASE}?language=en&url_key=sofas").json()
        assert data["results"][0]["has_children"] is True
