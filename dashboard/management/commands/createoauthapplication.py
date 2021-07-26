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
from ...utils.base64 import base64_decode


class Command(BaseCommand):
    help = 'Create OAuth application.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--name',
                            dest='name',
                            required=True,
                            help='The name for the OAuth application.')
        parser.add_argument('--redirect-uri',
                            dest='redirect_uri',
                            required=True,
                            help='The redirect URI for the OAuth application.')
        parser.add_argument('--secret-name',
                            dest='secret_name',
                            default=None,
                            help='The name of the Kubernetes secret to store the OAuth secrets in.')
        parser.add_argument('--secret-namespace',
                            dest='secret_namespace',
                            default=None,
                            help='The namespace of the Kubernetes secret.')

    def handle(self, *args, **options):
        name = options.get('name')
        redirect_uri = options.get('redirect_uri')
        secret_name = options.get('secret_name')
        secret_namespace = options.get('secret_namespace')

        try:
            user = User.objects.get(username='admin')
        except User.DoesNotExist:
            print('Skipping creation of OAuth application "%s": No "admin" user found.' % name)
            return

        kubernetes_client = KubernetesClient()

        secret_found = False
        try:
            application = Application.objects.get(name=name, user=user)
            if application.redirect_uris != redirect_uri:
                application.redirect_uris = redirect_uri
                application.save()
        except Application.DoesNotExist:
            # Check if a secret already exists.
            client_id = None
            client_secret = None
            if secret_name:
                for secret in kubernetes_client.list_secrets(secret_namespace):
                    if secret.metadata.name == secret_name:
                        client_id = base64_decode(secret.data.get('client-id')).decode()
                        client_secret = base64_decode(secret.data.get('client-secret')).decode()
                        secret_found = True
                        break
            application = Application(name=name,
                                      user=user,
                                      client_id=client_id,
                                      client_secret=client_secret,
                                      client_type=Application.CLIENT_CONFIDENTIAL,
                                      authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                                      algorithm=Application.RS256_ALGORITHM,
                                      skip_authorization=True,
                                      redirect_uris=redirect_uri)
            application.save()
            print('OAuth application created.')
        else:
            print('Skipping creation of OAuth application "%s": Already configured.' % name)

        if not secret_name or secret_found:
            return
        kubernetes_client.update_secret(secret_namespace, secret_name, ['client-id=%s' % application.client_id,
                                                                        'client-secret=%s' % application.client_secret])
        print('Updated secret for OAuth application "%s".' % name)
