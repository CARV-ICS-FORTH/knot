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
from django.conf import settings
from oauth2_provider.models import Application
from urllib.parse import urlparse

from ...models import User
from ...utils.kubernetes import KubernetesClient


class Command(BaseCommand):
    help = 'Create initial OAuth application for Vouch.'

    def handle(self, *args, **options):
        if not settings.VOUCH_URL:
            print('Skipping creation of OAuth application for Vouch: No Vouch URL configured.')
            return

        try:
            user = User.objects.get(username='admin')
        except User.DoesNotExist:
            print('Skipping creation of OAuth application for Vouch: No "admin" user found.')
            return

        vouch_url = urlparse(settings.VOUCH_URL)
        try:
            vouch_application = Application.objects.get(name='vouch', user=user)
        except Application.DoesNotExist:
            vouch_application = Application(name='vouch',
                                            user=user,
                                            client_type=Application.CLIENT_CONFIDENTIAL,
                                            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                                            algorithm=Application.RS256_ALGORITHM,
                                            skip_authorization=True,
                                            redirect_uris='%s://%s/auth' % (vouch_url.scheme, vouch_url.netloc))
            vouch_application.save()
            print('OAuth application for Vouch created.')
        else:
            print('Skipping creation of OAuth application for Vouch: Application already configured.')

        kubernetes_client = KubernetesClient()
        kubernetes_client.update_secret(None, 'karvdash-vouch', ['oauth-client-id=%s' % vouch_application.client_id,
                                                                 'oauth-client-secret=%s' % vouch_application.client_secret])
