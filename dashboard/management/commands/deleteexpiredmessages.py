# Copyright [2019] [FORTH-ICS]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from ...models import Message


class Command(BaseCommand):
    help = 'Deletes messages after a week.'

    def handle(self, *args, **options):
        expired_messages = Message.objects.filter(created__lt=(timezone.now() - timedelta(days=7)))
        count = expired_messages.count()
        expired_messages.delete()

        print('%i messages were deleted.' % count)
