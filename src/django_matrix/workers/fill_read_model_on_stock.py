# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from process_logger import ProcessLogger, ProcessLoggerMixin

from django_matrix.models import Channel, ProductRepresentation

# RuntimeError: an app that is installed but not in INSTALLED_APPS raises it on model import, not ImportError.
try:
    from django_qms.output import get_product_quantity, get_quantities

    _HAS_QMS = True
except (ImportError, RuntimeError):
    _HAS_QMS = False

BULK_BATCH_SIZE = 1000


class FillReadModelOnStock(ProcessLoggerMixin):
    app_name: str = "django_matrix"
    channel: Channel

    def __init__(self, channel: Channel, product_id: str = None):
        self.update = {}
        self.products = None
        self.channel = channel
        self.quantities = None
        self.parent_quantities = {}
        self.product_id = product_id

    def set_logger(self, logger: ProcessLogger):
        super().set_logger(logger)

    def get_quantities_qms(self):
        if not _HAS_QMS:
            self.logger.info("django_qms not available, returning empty quantities")
            return {}
        try:
            if self.product_id:
                qty = get_product_quantity(self.channel.idx, self.product_id)
                self.quantities = [(self.product_id, qty)]
            else:
                self.quantities = get_quantities(self.channel.idx)

            qtys = {}
            for sku, quantity in self.quantities:
                qtys[sku] = quantity
            self.quantities = qtys
            return self.quantities
        except Exception as e:
            self.logger.set_code(4018)
            self.logger.exception(e)
            return self.quantities

    def get_quantities_checkout(self):
        from django_checkout.models import Stock
        from django_pim.models import BundleLink

        bundles = BundleLink.objects.all().values_list(
            "product_bundle__real_product__sku", "subproduct__real_product__sku", "quantity"
        )
        bundles_grouped_by_sku = groupby(bundles, key=lambda x: x[0])

        add_param = {"product__sku": self.product_id} if self.product_id else {}
        quantities = Stock.annotated.filter(product__channel__idx=self.channel.idx, **add_param).values_list(
            "product__sku", "saleable_quantity"
        )

        qtys = {}
        for sku, quantity in quantities:
            qtys[sku] = quantity
        self.quantities = qtys

        for sku_bundle, sub_skus_iter in bundles_grouped_by_sku:
            if sku_bundle in self.quantities.keys():
                self.logger.add_log_param("sku_bundle", sku_bundle)
                sub_skus = list(sub_skus_iter)
                sub_bundles_qty = []
                for sku, sub_sku, sub_quantity in sub_skus:
                    if sub_sku not in self.quantities.keys():
                        self.logger.set_code(4027)
                        self.logger.add_log_param("sub_sku", sub_sku)
                        self.logger.error(f"Bundle sub sku {sub_sku} not found in stock. Bundle {sku_bundle} skipped.")
                        self.logger.delete_few_log_param(["sku_bundle", "sub_sku"])
                        continue
                    sub_bundles_qty.append(self.quantities[sub_sku] // sub_quantity)
                min_qty = min(sub_bundles_qty) if sub_bundles_qty else 0
                self.quantities[sku_bundle] = min_qty
                self.logger.delete_log_param("sku_bundle")
        return self.quantities

    def get_all_products_representation(self):
        if self.products:
            return self.products
        query = {"sku": self.product_id} if self.product_id else {}
        self.products = (
            ProductRepresentation.objects.prefetch_related("parent")
            .filter(channel=self.channel, **query)
            .iterator(chunk_size=BULK_BATCH_SIZE)
        )
        return self.products

    def iterate_products_representation_and_update_on_stock(self):
        for pr in self.products:
            qty = self.quantities.get(pr.sku, 0)
            if qty > 0:
                pr.on_stock = True
            else:
                pr.on_stock = False
            pr.stock_qty = qty
            self.update[pr.sku] = pr

            if pr.parent:
                parent_sku = pr.parent.sku
                if parent_sku in self.parent_quantities:
                    self.parent_quantities[parent_sku] = self.parent_quantities[parent_sku] + qty
                else:
                    self.parent_quantities[parent_sku] = qty

    def iterate_parent_products_representation_and_update_on_stock(self):
        for sku, qty in self.parent_quantities.items():
            if sku in self.update:
                pr = self.update[sku]
                if qty > 0:
                    pr.on_stock = True
                else:
                    pr.on_stock = False
                pr.stock_qty = qty
                self.update[sku] = pr

    def update_product_on_stock(self):
        try:
            updated = ProductRepresentation.objects.bulk_update(
                self.update.values(), fields=["on_stock", "stock_qty"], batch_size=BULK_BATCH_SIZE
            )
            self.logger.set_code(2014)
            self.logger.set_db_operation("BULK_UPDATE", self.app_name, "ProductRepresentation")
            self.logger.info(f"ProductRepresentation - on_stock and stock_qty - updated {updated} products")
        except Exception as e:
            self.logger.set_code(4016)
            self.logger.exception(e)

    def run(self):

        try:
            from django_checkout.models import Stock

            process_checkout = True
        except (ImportError, RuntimeError):
            # If we don't have django_checkout, ex. Catalog shop - we can import from QMS directly
            process_checkout = False

        if not process_checkout and not _HAS_QMS:
            self.logger.info("Skipping stock fill: neither django_checkout nor django_qms available")
            return

        try:
            if process_checkout:
                self.quantities = self.get_quantities_checkout()
            else:
                self.quantities = self.get_quantities_qms()
        except Exception as e:
            self.logger.set_code(4028)
            self.logger.exception(e)
            return

        self.get_all_products_representation()
        self.iterate_products_representation_and_update_on_stock()
        self.iterate_parent_products_representation_and_update_on_stock()
        self.update_product_on_stock()


def fill_read_model_on_stock_batch(channel: Channel, product_id: str = None):
    logger = ProcessLogger("FILL_READ_MODEL_ON_STOCK_BATCH", "django_matrix")
    on_stock_domain = FillReadModelOnStock(channel, product_id)
    on_stock_domain.set_logger(logger)
    on_stock_domain.run()
