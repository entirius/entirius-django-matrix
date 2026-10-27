# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""fetch_categories side-loads PIM categories onto the v1 product listing and details responses.

Without the parameter the responses keep their old shape — no ``categories`` key at all — so a
storefront that does not ask for them pays nothing.
"""

import pytest

LISTING = "/api/matrix/v1/test-v2/products/?language=en&currency=EUR&country=PL"
DETAILS = "/api/matrix/v1/test-v2/products/test-chair/?language=en&currency=EUR&country=PL"


@pytest.fixture
def product_in_pim_category(channel_full, simple_product):
    """Put the matrix product into a PIM category tree: root -> outdoor-seating."""
    try:
        from django_pim.models import Channel as PimChannel
        from django_pim.models import FeatureSet, Product, ProductCategory, ProductInCategory, RealProduct
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
    category = ProductCategory.objects.create(
        shop=pim_ch,
        idx="outdoor-seating",
        url_key_t9n={"en": "outdoor-seating"},
        name_t9n={"en": "Outdoor Seating"},
        parent_category=root,
        is_active=True,
        is_in_menu=True,
        tree_deep=1,
        position=1,
    )
    product = Product.objects.create(
        real_product=RealProduct.objects.create(sku=simple_product.sku),
        shop=pim_ch,
        feature_set=FeatureSet.objects.create(idx="outdoor-furniture", name="Outdoor Furniture"),
    )
    ProductInCategory.objects.create(product=product, category=category)
    return category


class TestListingFetchCategories:
    def test_no_categories_key_without_the_param(self, api, product_in_pim_category):
        product = api.get(LISTING).json()["data"][0]
        assert "categories" not in product

    def test_categories_returned_with_the_param(self, api, product_in_pim_category):
        product = api.get(f"{LISTING}&fetch_categories=true").json()["data"][0]
        assert [category["idx"] for category in product["categories"]] == ["outdoor-seating"]

    def test_category_carries_breadcrumbs(self, api, product_in_pim_category):
        product = api.get(f"{LISTING}&fetch_categories=true").json()["data"][0]
        category = product["categories"][0]
        assert category["url_key"] == "outdoor-seating"
        assert category["breadcrumb_path"] == "Outdoor Seating"

    def test_product_missing_from_pim_gets_empty_list(self, api, simple_product):
        """No PIM product for the SKU — the response stays 200 with an empty category list."""
        response = api.get(f"{LISTING}&fetch_categories=true")
        assert response.status_code == 200
        assert response.json()["data"][0]["categories"] == []


class TestDetailsFetchCategories:
    def test_no_categories_key_without_the_param(self, api, product_in_pim_category):
        product = api.get(DETAILS).json()["data"]
        assert "categories" not in product

    def test_categories_returned_with_the_param(self, api, product_in_pim_category):
        product = api.get(f"{DETAILS}&fetch_categories=true").json()["data"]
        assert [category["idx"] for category in product["categories"]] == ["outdoor-seating"]

    def test_product_missing_from_pim_gets_empty_list(self, api, simple_product):
        response = api.get(f"{DETAILS}&fetch_categories=true")
        assert response.status_code == 200
        assert response.json()["data"]["categories"] == []
