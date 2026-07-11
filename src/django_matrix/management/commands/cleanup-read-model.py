# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand

from django_matrix.models import Channel
from django_matrix.workers.cleanup_read_model import cleanup_read_model


class Command(BaseCommand):
    help = "Cleanup Read Model. Remove product that are disabled or non exist in PIM"

    def add_arguments(self, parser):
        parser.add_argument("--channel_idx", type=str, help="Volkanos Channel/Shop IDX")

    @bi_django_command_decorator
    def handle(self, *args, **options):
        channel_idx = options["channel_idx"]
        if channel_idx:
            channels: list[Channel] = Channel.objects.filter(idx=channel_idx)
        else:
            channels: list[Channel] = Channel.objects.all()

        if len(channels) == 0:
            self.stdout.write("No Channels in Matrix.")

        for channel in channels:
            self.stdout.write(f"Channel: {channel.idx}")

            self.stdout.write("Start cleanup")
            cleanup_read_model(channel=channel)
