# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_matrix.models.base_model_abstract import BaseModel


class ProductPrice(BaseModel):
    product_representation = models.ForeignKey(
        "ProductRepresentation", db_index=True, on_delete=models.CASCADE, related_name="prices", null=False
    )
    currency = models.ForeignKey(
        "django_regional.Currency", related_name="matrix_product", on_delete=models.SET_NULL, blank=True, null=True
    )
    country = models.ForeignKey(
        "django_regional.Country", related_name="matrix_product", on_delete=models.SET_NULL, blank=True, null=True
    )
    is_range = models.BooleanField(null=False, default=False)
    has_special_price = models.BooleanField(null=False, default=False)
    # price
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, null=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, null=True)
    range_from = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, null=True)
    range_to = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, null=True)
    is_price_offer = models.BooleanField(null=False, default=False)
    max_price_offer = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    min_price_offer = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    # special_price
    promo_badge = models.CharField(max_length=256, null=True)
    special_from_date = models.CharField(max_length=256, null=True)
    special_to_date = models.CharField(max_length=256, null=True)
    special_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    special_price_range_from = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    special_price_range_to = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    # omnibus
    omnibus_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    omnibus_price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    omnibus_price_to = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    # tax
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    tax_rule = models.CharField(max_length=256, null=True)
    price_tax_config_opposite = models.CharField(max_length=256, null=True, blank=True)
    price_tax_config_opposite_from = models.CharField(max_length=256, null=True, blank=True)
    price_tax_config_opposite_to = models.CharField(max_length=256, null=True, blank=True)
    special_price_tax_config_opposite = models.CharField(max_length=256, null=True, blank=True)
    special_price_tax_config_opposite_from = models.CharField(max_length=256, null=True, blank=True)
    special_price_tax_config_opposite_to = models.CharField(max_length=256, null=True, blank=True)
    is_only_for_verified_user = models.BooleanField(
        null=False,
        default=False,
        help_text="This field contains information whether the price was retrieved from a price list that is available only to verified users.",
    )
    updated_at = models.DateTimeField(null=True, blank=True)

    # v2 columns — explicit gross/net, always both populated regardless of PRICE_TYPE
    gross = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_gross = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    special_gross = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    special_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percent_off = models.IntegerField(null=True, blank=True)
    range_from_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    range_to_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    range_from_special_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    range_to_special_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    objects = models.Manager()

    class Meta:
        ordering = ["product_representation__sku"]
        verbose_name_plural = "Products Prices"
        constraints = [
            models.UniqueConstraint(
                fields=["product_representation", "currency", "country"], name="unique_product_price_currency_country"
            )
        ]

    def __str__(self):
        return self.product_representation.sku
