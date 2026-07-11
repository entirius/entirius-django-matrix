# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.core.management.base import BaseCommand

from django_matrix.workers.fill_products_magento_ids import import_ids_from_csv

logger_process = logging.getLogger("process")
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import magento id's for product sku from CSV"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)
        parser.add_argument("--channel_idx", type=str, help="Volkanos Channel/Shop IDX - specify channel_idx")

    def handle(self, *args, **options):
        file_path = options["file_path"]
        channel_idx = options["channel_idx"]
        errors = 0
        number_ids_csv = 0
        try:
            errors, number_ids_csv = import_ids_from_csv(file_path=file_path, channel_idx=channel_idx)
        except Exception as e:
            logger.exception(e)
            logger_process.error(
                "Error while importing ids",
                extra={"details": {"errors": str(e)}},
            )

        print(f"Zostało zaimportowanych id w liczbie {number_ids_csv - errors} na {number_ids_csv} z pliku {file_path}")
