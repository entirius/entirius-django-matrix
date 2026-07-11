# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Worker tests for fill_read_model_attachments — write, skip, and stale-clear paths."""

import pytest

from django_matrix.models import Channel, ProductRepresentation


@pytest.fixture
def matrix_channel(db):
    """Minimal channel for worker tests (no regional deps)."""
    return Channel.objects.create(
        idx="worker-test", label="Worker Test", default_order="sku", default_order_direction="ASC"
    )


@pytest.fixture
def pim_channel(db):
    """PIM channel matching the Matrix channel idx — requires Currency + Language for NOT NULL constraints."""
    try:
        from django_pim.models import Channel as PimChannel
        from django_pim.models import FeatureSet
        from django_regional.models import Currency, Language
    except ImportError:
        pytest.skip("django_pim or django_regional not available")

    currency, _ = Currency.objects.get_or_create(
        iso3="USD", defaults={"name_en": "Dollar", "name_pl": "Dolar", "symbol": "$"}
    )
    lang, _ = Language.objects.get_or_create(
        iso2="en", defaults={"iso3": "eng", "name_en": "english", "name_pl": "angielski", "name_source": "English"}
    )
    # FeatureSet is required by Product (NOT NULL FK)
    FeatureSet.objects.get_or_create(idx="default", defaults={"name": "Default", "is_default": True})
    ch, _ = PimChannel.objects.get_or_create(
        idx="worker-test",
        defaults={"name": "Worker Test", "default_currency": currency, "default_language": lang},
    )
    return ch


@pytest.fixture
def product_with_attachments(matrix_channel):
    """PR with pre-existing attachments (simulates previous worker run)."""
    return ProductRepresentation.objects.create(
        sku="WORKER-ATT-001",
        channel=matrix_channel,
        product_type="SIMPLE",
        on_stock=True,
        attachments=[{"file_label": "Old Manual", "file_type": "pdf"}],
    )


@pytest.fixture
def product_without_attachments(matrix_channel):
    """PR with no attachments."""
    return ProductRepresentation.objects.create(
        sku="WORKER-ATT-002",
        channel=matrix_channel,
        product_type="SIMPLE",
        on_stock=True,
    )


class TestFillAttachmentsWorker:
    """Tests for fill_read_model_attachments worker."""

    def test_happy_path_writes_attachments(self, matrix_channel, pim_channel, product_without_attachments):
        """Worker writes attachment JSON when PIM has files for the product."""
        try:
            from django_pim.models import Product, RealProduct
            from django_pim.models.files import FileRoleEnum, Files
            from django_pim.models.files_category import FilesCategory
            from django_pim.models.product_file import ProductFile
        except ImportError:
            pytest.skip("django_pim not available")

        from django_pim.models import FeatureSet

        fs = FeatureSet.objects.get(idx="default")
        rp, _ = RealProduct.objects.get_or_create(sku="WORKER-ATT-002")
        pim_product = Product.objects.create(real_product=rp, shop=pim_channel, feature_set=fs, is_enabled=True)

        cat = FilesCategory.objects.create(code="test-cat", name_t9n={"en": "Test Cat"})
        f = Files.objects.create(
            file_label="Test PDF",
            file_label_t9n={"en": "Test PDF", "pl": "Testowy PDF"},
            file_type=FileRoleEnum.PDF,
            original_file_name="test.pdf",
            weight="1.5",
            file_category=cat,
        )
        ProductFile.objects.create(product=pim_product, file=f)

        from django_matrix.workers.fill_read_model_attachments import fill_read_model_attachments

        fill_read_model_attachments(channel=matrix_channel, product_id="WORKER-ATT-002")

        product_without_attachments.refresh_from_db()
        assert isinstance(product_without_attachments.attachments, list)
        assert len(product_without_attachments.attachments) == 1
        att = product_without_attachments.attachments[0]
        assert att["file_label"] == "Test PDF"
        assert att["file_type"] == "pdf"
        assert att["category_code"] == "test-cat"

    def test_skip_when_no_pr_match(self, matrix_channel, pim_channel):
        """Worker skips ProductFiles whose SKU has no ProductRepresentation."""
        try:
            from django_pim.models import Product, RealProduct
            from django_pim.models.files import FileRoleEnum, Files
            from django_pim.models.product_file import ProductFile
        except ImportError:
            pytest.skip("django_pim not available")

        from django_pim.models import FeatureSet

        fs = FeatureSet.objects.get(idx="default")
        rp, _ = RealProduct.objects.get_or_create(sku="ORPHAN-SKU-999")
        pim_product = Product.objects.create(real_product=rp, shop=pim_channel, feature_set=fs, is_enabled=True)
        f = Files.objects.create(file_label="Orphan File", file_type=FileRoleEnum.DOC, original_file_name="orphan.doc")
        ProductFile.objects.create(product=pim_product, file=f)

        from django_matrix.workers.fill_read_model_attachments import fill_read_model_attachments

        # Should not raise — orphan SKU silently skipped
        fill_read_model_attachments(channel=matrix_channel, product_id="ORPHAN-SKU-999")

    def test_stale_attachments_cleared(self, matrix_channel, product_with_attachments):
        """PR that previously had attachments gets cleared when PIM has no files."""
        assert product_with_attachments.attachments == [{"file_label": "Old Manual", "file_type": "pdf"}]

        from django_matrix.workers.fill_read_model_attachments import fill_read_model_attachments

        fill_read_model_attachments(channel=matrix_channel, product_id="WORKER-ATT-001")

        product_with_attachments.refresh_from_db()
        assert product_with_attachments.attachments == []
