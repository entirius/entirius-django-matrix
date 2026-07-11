# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils import timezone


def timestamp_print(text):
    print(timestamp_print_return(text))


def timestamp_print_return(text):
    now = timezone.now().isoformat()
    return f"[{now}] {str(text)}"
