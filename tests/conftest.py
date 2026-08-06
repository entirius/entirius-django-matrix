# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api(db):
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username="admin", password="admin123", email="admin@test.com")


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="user", password="user123", email="user@test.com")


@pytest.fixture
def channel(db):
    from django_matrix.models import Channel

    return Channel.objects.create(
        idx="test-channel", label="Test Channel", default_order="sku", default_order_direction="ASC"
    )


# ── Shared v2 fixtures ──────────────────────────────────────────────


@pytest.fixture
def channel_full(db):
    """Channel with full regional config (Language, Currency, Country)."""
    try:
        from django_regional.models import Country, Currency, Language

        lang, _ = Language.objects.get_or_create(
            iso2="en", defaults={"iso3": "eng", "name_en": "english", "name_pl": "angielski", "name_source": "English"}
        )
        currency, _ = Currency.objects.get_or_create(
            iso3="EUR", defaults={"name_en": "Euro", "name_pl": "Euro", "symbol": "€"}
        )
        country, _ = Country.objects.get_or_create(iso2="PL", defaults={"iso3": "POL", "name": "Poland"})
    except ImportError:
        pytest.skip("django_regional not available")
        return

    from django_matrix.models import Channel

    ch = Channel.objects.create(
        idx="test-v2",
        label="Test v2",
        default_language=lang,
        default_currency=currency,
        default_country=country,
        default_order="sku",
        default_order_direction="ASC",
    )
    ch.languages.add(lang)
    ch.currencies.add(currency)
    ch.countries.add(country)
    return ch, lang, currency, country


@pytest.fixture
def simple_product(channel_full):
    """Simple product with T9N, price, 4 attributes (color, weight, meta_kw, is_handmade), and PL T9N."""
    from django_matrix.models import Attribute, ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full
    pr = ProductRepresentation.objects.create(
        sku="V2-SIMPLE-001",
        channel=ch,
        product_type="SIMPLE",
        kind_of_product="PHYSICAL",
        on_stock=True,
        is_virtual=False,
        categories_data=[{"idx": "chairs", "name": "Chairs", "url_key": "chairs"}],
        feature_set={"idx": "furniture", "name": "Furniture"},
        url_keys={"test-chair": "en", "testowe-krzeslo": "pl"},
        main_image={
            "source_set": [{"source": "/media/img/chair-main.webp", "width": 800, "height": 600}],
            "alt_text": "Test Chair front view",
        },
        pictures=[
            {
                "type": "picture",
                "position": 0,
                "role": "main",
                "source_set": [{"source": "/media/img/chair-main.webp", "width": 800, "height": 600}],
                "alt_text": "Test Chair front view",
            },
            {
                "type": "picture",
                "position": 1,
                "role": "general",
                "source_set": [{"source": "/media/img/chair-side.webp", "width": 800, "height": 600}],
                "alt_text": None,
            },
        ],
        videos=[
            {
                "type": "video",
                "position": 2,
                "role": "main",
                "source_set": [
                    {"title": "Chair Assembly", "url": "https://youtube.com/watch?v=abc", "source": "YouTube"}
                ],
            },
        ],
        attachments=[
            {
                "file_label": "Assembly Guide",
                "file_label_t9n": {"en": "Assembly Guide", "pl": "Instrukcja montazu"},
                "original_file_name": "assembly-guide-v2.pdf",
                "file_path": "/media/files/abc123.pdf",
                "file_type": "pdf",
                "file_size": "2.45",
                "category_code": "manuals",
                "category_name_t9n": {"en": "Manuals", "pl": "Instrukcje"},
            },
        ],
    )
    ProductT9N.objects.create(
        product_representation=pr,
        language=lang,
        name="Test Chair",
        url_key="test-chair",
        desc="<p>Description</p>",
        short_desc="Short desc",
        meta_title="Test Chair | Store",
        meta_description="Meta desc",
        badges=[{"idx": "new", "name": "New", "extension": None}],
        brands=[{"idx": "brand-a", "name": "Brand A", "extension": None}],
    )
    ProductPrice.objects.create(
        product_representation=pr,
        currency=currency,
        country=country,
        price=Decimal("100.00"),
        final_price=Decimal("80.00"),
        has_special_price=True,
        special_price=Decimal("80.00"),
        tax_amount=Decimal("0.23"),
        tax_rule="23%",
        promo_badge="20%",
        gross=Decimal("100.00"),
        net=Decimal("81.30"),
        final_gross=Decimal("80.00"),
        final_net=Decimal("65.04"),
        special_gross=Decimal("80.00"),
        special_net=Decimal("65.04"),
        percent_off=20,
    )
    Attribute.objects.create(
        product=pr,
        hash="attr1",
        feature_idx="color",
        feature_type="SELECT",
        feature_name_t9n={"en": "Color"},
        attribute_idx="red",
        attribute_value_text="Red",
        is_visible=True,
        has_visual_asset=True,
        is_comparable=True,
        is_seo=False,
        extension={"color_hash": "#CC0000"},
        group_idx="appearance",
        group_name_t9n={"en": "Appearance", "pl": "Wygląd"},
        group_position=10,
    )
    Attribute.objects.create(
        product=pr,
        hash="attr2",
        feature_idx="weight",
        feature_type="DECIMAL",
        feature_name_t9n={"en": "Weight"},
        attribute_value_text="5.5",
        is_visible=True,
        has_visual_asset=False,
        is_comparable=False,
        is_seo=False,
    )
    Attribute.objects.create(
        product=pr,
        hash="attr3",
        feature_idx="meta_kw",
        feature_type="TEXT",
        feature_name_t9n={"en": "Meta Keywords"},
        attribute_value_text="chair,office",
        is_visible=False,
        has_visual_asset=False,
        is_comparable=False,
        is_seo=True,
    )
    Attribute.objects.create(
        product=pr,
        hash="attr4",
        feature_idx="is_handmade",
        feature_type="BOOL",
        feature_name_t9n={"en": "Handmade"},
        attribute_value_text="True",
        is_visible=True,
        has_visual_asset=False,
        is_comparable=False,
        is_seo=False,
    )
    # Second language T9N for url_keys test (Decision #20)
    try:
        from django_regional.models import Language

        lang_pl = Language.objects.create(
            iso2="pl", iso3="pol", name_en="polish", name_pl="polski", name_source="Polish"
        )
        ProductT9N.objects.create(
            product_representation=pr, language=lang_pl, name="Testowe Krzesło", url_key="testowe-krzeslo"
        )
    except Exception:
        pass
    return pr


@pytest.fixture
def configurable_product(channel_full):
    """CONFIGURABLE parent + 2 SIMPLE children with range pricing."""
    from django_matrix.models import ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full
    parent = ProductRepresentation.objects.create(
        sku="V2-CFG-001",
        channel=ch,
        product_type="CONFIGURABLE",
        kind_of_product="PHYSICAL",
        on_stock=True,
        is_virtual=False,
        url_keys={"config-sofa": "en"},
    )
    ProductT9N.objects.create(
        product_representation=parent,
        language=lang,
        name="Config Sofa",
        url_key="config-sofa",
    )
    ProductPrice.objects.create(
        product_representation=parent,
        currency=currency,
        country=country,
        is_range=True,
        range_from=Decimal("500.00"),
        range_to=Decimal("1200.00"),
        range_from_net=Decimal("406.50"),
        range_to_net=Decimal("975.61"),
    )
    for sku, price_val in [("V2-CFG-001-S", 500), ("V2-CFG-001-L", 1200)]:
        child = ProductRepresentation.objects.create(
            sku=sku,
            channel=ch,
            product_type="SIMPLE",
            parent=parent,
            kind_of_product="PHYSICAL",
            on_stock=True,
        )
        ProductT9N.objects.create(
            product_representation=child,
            language=lang,
            name=f"Config Sofa {sku[-1]}",
            url_key=f"config-sofa-{sku[-1].lower()}",
        )
        net_val = round(Decimal(price_val) / Decimal("1.23"), 2)
        ProductPrice.objects.create(
            product_representation=child,
            currency=currency,
            country=country,
            gross=Decimal(str(price_val)),
            net=net_val,
            final_gross=Decimal(str(price_val)),
            final_net=net_val,
        )
    return parent


@pytest.fixture
def product_with_reviews(channel_full):
    """Product with average_rating and review_count for decimal string test."""
    from django_matrix.models import ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = channel_full
    pr = ProductRepresentation.objects.create(
        sku="V2-REVIEW-001",
        channel=ch,
        product_type="SIMPLE",
        kind_of_product="PHYSICAL",
        on_stock=True,
        average_rating=Decimal("4.50"),
        number_of_reviews=12,
        url_keys={"reviewed-chair": "en"},
    )
    ProductT9N.objects.create(
        product_representation=pr,
        language=lang,
        name="Reviewed Chair",
        url_key="reviewed-chair",
    )
    ProductPrice.objects.create(
        product_representation=pr,
        currency=currency,
        country=country,
        gross=Decimal("200.00"),
        net=Decimal("162.60"),
        final_gross=Decimal("200.00"),
        final_net=Decimal("162.60"),
    )
    return pr


# ── Search fixtures (33731) ─────────────────────────────────────────


@pytest.fixture
def searchable_channel(channel_full):
    """Channel where `name` is searchable.

    Without a SearchableFeatures row, get_featuers_restrictions() returns searchable=['sku']
    only and the repository skips the `pt.name ILIKE` clause entirely — every name query
    silently matches nothing.
    """
    from django_pim.models import Feature, FeatureScopeEnum, FeatureTypeEnum

    from django_matrix.models import SearchableFeatures

    ch, lang, currency, country = channel_full
    # `name` is a reserved system idx in PIM — scope must be SYSTEM, as it is in real data.
    feature = Feature.objects.create(
        idx="name",
        name_t9n={"en": "Name", "pl": "Nazwa"},
        feature_type=FeatureTypeEnum.TEXT,
        scope=FeatureScopeEnum.SYSTEM,
    )
    SearchableFeatures.objects.create(channel=ch, feature=feature)
    return channel_full


@pytest.fixture
def many_sofas(searchable_channel):
    """5 products named 'Sofa <n>' — enough for total > page_size."""
    from django_matrix.models import ProductPrice, ProductRepresentation, ProductT9N

    ch, lang, currency, country = searchable_channel
    products = []
    for n in range(1, 6):
        pr = ProductRepresentation.objects.create(
            sku=f"V2-SOFA-{n:03d}",
            channel=ch,
            product_type="SIMPLE",
            kind_of_product="PHYSICAL",
            on_stock=True,
            url_keys={f"sofa-{n}": "en"},
        )
        ProductT9N.objects.create(
            product_representation=pr,
            language=lang,
            name=f"Sofa {n}",
            url_key=f"sofa-{n}",
        )
        ProductPrice.objects.create(
            product_representation=pr,
            currency=currency,
            country=country,
            gross=Decimal("100.00"),
            net=Decimal("81.30"),
            final_gross=Decimal("100.00"),
            final_net=Decimal("81.30"),
        )
        products.append(pr)
    return products


@pytest.fixture
def spy_list_products(monkeypatch):
    """Capture the kwargs search_service passes down, without touching the DB.

    Relevance direction is a no-op in SQL unless MATRIX_FULL_TEXT_SEARCH is on, so the
    service-level kwarg is the right place to pin it.
    """
    from django_matrix.services import search_service

    captured: dict = {}

    def fake_list_products(**kwargs):
        captured.update(kwargs)
        return [], False, []

    monkeypatch.setattr(search_service, "list_products", fake_list_products)
    return captured


@pytest.fixture
def fts_on(monkeypatch):
    """Enable full-text search for one test.

    `raw_sql/product.py` does `from django_matrix import settings` and reads the flag as a
    module attribute at call time, so patching the attribute works. Django's override_settings
    does NOT — it patches django.conf.settings, which the module already snapshot-read.
    ?language=pl is safe here: name_en="polish" is not a Postgres text-search configuration, and
    since 33733 an unknown name falls back to `simple` instead of raising (test_full_text_search).
    """
    monkeypatch.setattr("django_matrix.settings.MATRIX_FULL_TEXT_SEARCH", True)
