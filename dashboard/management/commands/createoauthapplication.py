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
from oauth2_provider.models import Application
from oauth2_provider.generators import generate_client_secret

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
                            required=True,
                            help='The name of the Kubernetes secret to store the OAuth secrets in.')
        parser.add_argument('--secret-namespace',
                            dest='secret_namespace',
                            required=True,
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

        application = Application.objects.filter(name=name, user=user).first()

        kubernetes_client = KubernetesClient()
        secret = next((s for s in kubernetes_client.list_secrets(secret_namespace) if s.metadata.name == secret_name), None)

        recreate_application = True if application is None else False
        recreate_secret = True if secret is None or secret.data is None else False
        parameters = {}
        if recreate_secret:
            parameters = {'client_id': name,
                          'client_secret': generate_client_secret()}
            # The application needs to be recreated with the new client information.
            recreate_application = True
        else:
            parameters = {'client_id': base64_decode(secret.data.get('client-id')).decode(),
                          'client_secret': base64_decode(secret.data.get('client-secret')).decode()}
            # If the client information is out of sync, we need to recreate the application.
            if application and parameters['client_id'] != application.client_id:
                recreate_application = True

        if recreate_application:
            if not application:
                application = Application(name=name,
                                          user=user,
                                          client_type=Application.CLIENT_CONFIDENTIAL,
                                          authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                                          algorithm=Application.RS256_ALGORITHM,
                                          skip_authorization=True,
                                          redirect_uris=redirect_uri,
                                          post_logout_redirect_uris=redirect_uri,
                                          **parameters)
            else:
                application.client_id = parameters['client_id']
                application.client_secret = parameters['client_secret']
            application.save()
            print('OAuth application created.')
        else:
            print('Skipping creation of OAuth application "%s": Already configured.' % name)

        # In case just the redirect URI changes.
        if application.redirect_uris != redirect_uri:
            application.redirect_uris = redirect_uri
            application.post_logout_redirect_uris = redirect_uri
            application.save()

        if recreate_secret:
            kubernetes_client.update_secret(secret_namespace, secret_name, ['client-id=%s' % parameters['client_id'],
                                                                            'client-secret=%s' % parameters['client_secret']])
            print('Updated secret for OAuth application "%s".' % name)
