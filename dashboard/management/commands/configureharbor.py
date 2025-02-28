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

import sys

from django.core.management.base import BaseCommand
from time import sleep

from ...models import User
from ...utils.kubernetes import KubernetesClient
from ...utils.base64 import base64_decode
from ...utils.harbor import HarborClient


class Command(BaseCommand):
    help = 'Configure Harbor.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--secret-name',
                            dest='secret_name',
                            required=True,
                            help='The name of the Kubernetes secret to store the OAuth secrets in.')
        parser.add_argument('--secret-namespace',
                            dest='secret_namespace',
                            required=True,
                            help='The namespace of the Kubernetes secret.')
        parser.add_argument('--harbor-url',
                            dest='harbor_url',
                            required=True,
                            help='The URL for Harbor.')
        parser.add_argument('--harbor-admin-password',
                            dest='harbor_admin_password',
                            default=None,
                            help='The admin password for Harbor.')
        parser.add_argument('--ingress-url',
                            dest='ingress_url',
                            default='default',
                            help='The ingress URL.')
        parser.add_argument('--retries',
                            type=int,
                            dest='retries',
                            default=10,
                            help='Retries.')

    def handle(self, *args, **options):
        secret_name = options.get('secret_name')
        secret_namespace = options.get('secret_namespace')
        harbor_url = options.get('harbor_url')
        harbor_admin_password = options.get('harbor_admin_password')
        ingress_url = options.get('ingress_url')
        retries = options.get('retries')

        try:
            user = User.objects.get(username='admin')
        except User.DoesNotExist:
            print('Skipping configuration of Harbor: No "admin" user found.')
            return

        kubernetes_client = KubernetesClient()
        secret = next((s for s in kubernetes_client.list_secrets(secret_namespace) if s.metadata.name == secret_name), None)
        if secret is None or secret.data is None:
            print('Failed to configure Harbor: Secret not found or empty.')
            sys.exit(1)
        client_id = base64_decode(secret.data.get('client-id')).decode()
        client_secret = base64_decode(secret.data.get('client-secret')).decode()

        harbor_client = HarborClient(harbor_url, harbor_admin_password)
        result = None
        while not result and retries > 0:
            retries -= 1
            result = harbor_client.configure(client_id, client_secret, '%s/oauth' % ingress_url.rstrip('/'))
            if not result and retries > 0:
                print('Failed to configure Harbor. Retrying in 10 seconds... (retries: %d)' % retries)
                sleep(10)
        if not result:
            sys.exit(1)

        print('Configured Harbor.')
