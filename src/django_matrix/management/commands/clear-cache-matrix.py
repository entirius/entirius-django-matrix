# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Czyści cache dla widoków Django (cache_page)"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Wyczyść cały cache, nie tylko dla widoków")

    def handle(self, *args, **options):
        if options["all"]:
            # Wyczyść cały cache
            cache.clear()
            self.stdout.write(self.style.SUCCESS("Wyczyszczono cały cache Django"))
        else:
            # Próba bardziej selektywnego czyszczenia
            # Niektóre backendy mogą nie obsługiwać selektywnego czyszczenia
            try:
                # Sprawdź, czy cache obsługuje operacje na wzorcach
                if hasattr(cache, "delete_pattern"):
                    # Wzorzec dla cache_page
                    cache.delete_pattern("*views.decorators.cache.cache_page*")
                    self.stdout.write(self.style.SUCCESS("Wyczyszczono cache widoków"))
                else:
                    # Jeśli backend nie obsługuje wzorców, wyczyść cały cache
                    cache.clear()
                    self.stdout.write(
                        self.style.WARNING(
                            "Wyczyszczono cały cache, ponieważ backend nie obsługuje selektywnego czyszczenia"
                        )
                    )
            except AttributeError:
                # Jeśli funkcja delete_pattern nie istnieje
                cache.clear()
                self.stdout.write(
                    self.style.WARNING(
                        "Wyczyszczono cały cache, ponieważ backend nie obsługuje selektywnego czyszczenia"
                    )
                )
