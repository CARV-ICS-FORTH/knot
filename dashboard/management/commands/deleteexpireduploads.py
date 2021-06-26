# The MIT-Zero License
#
# Copyright (c) 2015 Julio M Alegria
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Based on delete_expired_uploads.py from https://github.com/juliomalegria/django-chunked-upload.

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import ugettext as _

from chunked_upload.settings import EXPIRATION_DELTA
from chunked_upload.models import ChunkedUpload
from chunked_upload.constants import UPLOADING, COMPLETE

prompt_msg = _(u'Do you want to delete {obj}?')


class Command(BaseCommand):
    help = 'Deletes chunked uploads that have already expired.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--interactive',
            action='store_true',
            dest='interactive',
            default=False,
            help='Prompt confirmation before each deletion.',
        )

    def handle(self, *args, **options):
        interactive = options.get('interactive')

        count = {UPLOADING: 0, COMPLETE: 0}
        qs = ChunkedUpload.objects.all()
        qs = qs.filter(created_on__lt=(timezone.now() - EXPIRATION_DELTA))

        for chunked_upload in qs:
            if interactive:
                prompt = prompt_msg.format(obj=chunked_upload) + u' (y/n): '
                answer = input(prompt).lower()
                while answer not in ('y', 'n'):
                    answer = input(prompt).lower()
                if answer == 'n':
                    continue

            count[chunked_upload.status] += 1
            # Deleting objects individually to call delete method explicitly
            chunked_upload.delete()

        print('%i complete uploads were deleted.' % count[COMPLETE])
        print('%i incomplete uploads were deleted.' % count[UPLOADING])
