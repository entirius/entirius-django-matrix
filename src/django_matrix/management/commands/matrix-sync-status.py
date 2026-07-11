# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from django_matrix.tasks import LAST_FLUSH_KEY, LOCK_KEY, PENDING_KEY


class Command(BaseCommand):
    help = "Show Matrix signal sync status: pending SKUs, flush state, settings"

    def handle(self, *args, **options):
        from django.conf import settings as django_settings

        # Kill-switch
        try:
            from django_pim.models.pim_settings import PimSettings

            enabled = PimSettings.load().matrix_signals_enabled
        except Exception:
            enabled = "N/A (django-pim not installed)"
        self.stdout.write(f"matrix_signals_enabled: {enabled}")

        # Settings
        debounce = getattr(django_settings, "PIM_MATRIX_SIGNALS_DEBOUNCE_SECONDS", 5)
        threshold = getattr(django_settings, "PIM_MATRIX_SIGNALS_BATCH_THRESHOLD", 500)
        denylist = getattr(django_settings, "PIM_MATRIX_SIGNALS_CHANNEL_DENYLIST", [])
        self.stdout.write(f"debounce_seconds: {debounce}")
        self.stdout.write(f"batch_threshold: {threshold}")
        self.stdout.write(f"channel_denylist: {denylist}")
        self.stdout.write("")

        # Redis state
        try:
            from django.core.cache import caches

            redis_client = caches["default"].client.get_client()

            pending_key = PENDING_KEY
            lock_key = LOCK_KEY
            last_flush_key = LAST_FLUSH_KEY

            pending_count = redis_client.zcard(pending_key)
            pending_members = redis_client.zrange(pending_key, 0, 50)
            flush_scheduled = redis_client.exists(lock_key)
            flush_ttl = redis_client.ttl(lock_key) if flush_scheduled else 0
            last_flush = redis_client.get(last_flush_key)

            self.stdout.write(f"pending_skus: {pending_count}")
            if pending_members:
                decoded = [m.decode("utf-8") if isinstance(m, bytes) else m for m in pending_members[:20]]
                self.stdout.write(f"  first 20: {decoded}")
                if pending_count > 20:
                    self.stdout.write(f"  ... and {pending_count - 20} more")

            self.stdout.write(f"flush_scheduled: {bool(flush_scheduled)}")
            if flush_scheduled:
                self.stdout.write(f"  ttl: {flush_ttl}s")

            if last_flush:
                import time

                ts = float(last_flush.decode("utf-8") if isinstance(last_flush, bytes) else last_flush)
                ago = int(time.time() - ts)
                self.stdout.write(f"last_flush: {ago}s ago")
            else:
                self.stdout.write("last_flush: never")

        except Exception as e:
            self.stdout.write(f"Redis unavailable: {e}")

        self.stdout.write("")

        # Celery queue depth
        try:
            from celery import current_app

            inspect = current_app.control.inspect()
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            matrix_active = 0
            matrix_reserved = 0
            for worker_tasks in active.values():
                matrix_active += sum(1 for t in worker_tasks if "matrix" in t.get("name", "").lower())
            for worker_tasks in reserved.values():
                matrix_reserved += sum(1 for t in worker_tasks if "matrix" in t.get("name", "").lower())
            self.stdout.write(f"celery_matrix_active: {matrix_active}")
            self.stdout.write(f"celery_matrix_reserved: {matrix_reserved}")
        except Exception as e:
            self.stdout.write(f"Celery inspect unavailable: {e}")
