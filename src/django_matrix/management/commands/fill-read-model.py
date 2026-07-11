# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from argparse import BooleanOptionalAction

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand

from django_matrix.tasks import fill_read_model_with_flags
from django_matrix.utils.timestamp_print import timestamp_print_return


class Command(BaseCommand):
    help = "Fill Read Model from PIM"

    def add_arguments(self, parser):
        parser.add_argument("--channel_idx", type=str, help="Volkanos Channel/Shop IDX")
        parser.add_argument("--custom", type=bool, action=BooleanOptionalAction, help="Only custom products")
        parser.add_argument("--bundle", type=bool, action=BooleanOptionalAction, help="Only bundle products")
        parser.add_argument("--config", type=bool, action=BooleanOptionalAction, help="Only config products")
        parser.add_argument("--simple", type=bool, action=BooleanOptionalAction, help="Only simple products")
        parser.add_argument("--prices", type=bool, action=BooleanOptionalAction, help="Only prices for products")
        parser.add_argument(
            "--onstock", type=bool, action=BooleanOptionalAction, help="Only on stock status for products"
        )
        parser.add_argument(
            "--pictures", type=bool, action=BooleanOptionalAction, help="Only pictures and thumbs for products"
        )
        parser.add_argument("--videos", type=bool, action=BooleanOptionalAction, help="Only videos for products")
        parser.add_argument(
            "--attachments", type=bool, action=BooleanOptionalAction, help="Only attachments for products"
        )
        parser.add_argument("--product_id", type=str, help="Volkanos Product SKU")

    @bi_django_command_decorator
    def handle(self, *args, **options):
        channel_idx = options["channel_idx"]
        product_id = options["product_id"]

        if product_id:
            self.stdout.write(timestamp_print_return(f"Start fill for product sku: {product_id}"))

        result = fill_read_model_with_flags(
            channel_idx=channel_idx,
            product_id=product_id,
            custom=options.get("custom", False),
            bundle=options.get("bundle", False),
            config=options.get("config", False),
            simple=options.get("simple", False),
            prices=options.get("prices", False),
            onstock=options.get("onstock", False),
            pictures=options.get("pictures", False),
            videos=options.get("videos", False),
            attachments=options.get("attachments", False),
        )

        if result["success"]:
            self.stdout.write(f"Successfully processed {result['channels_processed']} channels")
            for channel_result in result["results"]:
                steps = ", ".join(channel_result["steps"])
                self.stdout.write(f"Channel {channel_result['channel_idx']}: {steps}")
        else:
            self.stdout.write("Processing failed:")
            for channel_result in result["results"]:
                if not channel_result.get("success", False):
                    error = channel_result.get("error", "Unknown error")
                    self.stdout.write(f"Channel {channel_result['channel_idx']}: {error}")

        if product_id:
            self.stdout.write(timestamp_print_return(f"End fill for product sku: {product_id}"))
