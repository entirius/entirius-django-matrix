# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class MatrixSettings(models.Model):
    """Singleton runtime settings for Matrix. Managed via admin API / CMS panel."""

    use_price_tuner = models.BooleanField(
        default=False, help_text="Enable django-pricetuner integration for customer-group pricing"
    )

    class Meta:
        verbose_name = "Matrix Settings"
        verbose_name_plural = "Matrix Settings"

    def __str__(self) -> str:
        return "Matrix Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "MatrixSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
