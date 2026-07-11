# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_matrix.models import MatrixSettings


@admin.register(MatrixSettings)
class MatrixSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "use_price_tuner")

    def has_add_permission(self, request):
        return not MatrixSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
