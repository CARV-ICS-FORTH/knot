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

import os

from django.conf import settings
from restless.dj import DjangoResource
from restless.exceptions import Unauthorized, NotFound

from .models import APIToken
from .utils.kubernetes import KubernetesClient
from .utils.template import Template


def namespace_for_user(user):
    return 'karvdash-%s' % user.username

class ServiceResource(DjangoResource):
    http_methods = {'list': {'GET': 'list'},
                    'detail': {'DELETE': 'delete'}}

    def is_authenticated(self):
        if self.request.user and self.request.user.is_authenticated:
            return True

        token = None
        authorization_header = self.request.META.get('HTTP_AUTHORIZATION', '')
        if authorization_header and authorization_header.lower().startswith('token '):
            token = authorization_header[6:]
        if not token:
            token = self.request.GET.get('token', '')
        if not token:
            return False
        token = token.strip().lower()

        try:
            api_token = APIToken.objects.get(token=token)
        except APIToken.DoesNotExist:
            return False

        self.request.user = api_token.user
        return True

    def list(self):
        if not self.is_authenticated():
            raise Unauthorized()

        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.request.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_database = []
        for file_name in os.listdir(service_database_path):
            if file_name.endswith('.yaml'):
                service_database.append(file_name[:-5])

        contents = []
        for service in kubernetes_client.list_services(namespace=namespace_for_user(self.request.user), label_selector=''):
            name = service.metadata.name
            # ports = [str(p.port) for p in service.spec.ports if p.protocol == 'TCP']
            contents.append({'name': name,
                             'url': 'http://%s-%s.%s' % (name, self.request.user.username, settings.INGRESS_DOMAIN),
                             'created': service.metadata.creation_timestamp,
                             'actions': True if name in service_database else False})

        return contents

    def delete(self, pk):
        name = pk
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.request.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_yaml = os.path.join(service_database_path, '%s.yaml' % name)
        if not os.path.exists(service_yaml):
            raise NotFound()
        else:
            try:
                kubernetes_client.delete_yaml(service_yaml, namespace=namespace_for_user(self.request.user))
            except Exception as e:
                raise
            else:
                os.unlink(service_yaml)

class TemplateResource(DjangoResource):
    http_methods = {'list': {'GET': 'list'}}

    def list(self):
        contents = []
        for file_name in os.listdir(settings.SERVICE_TEMPLATE_DIR):
            if not file_name.endswith('.template.yaml'):
                continue

            file_path = os.path.join(settings.SERVICE_TEMPLATE_DIR, file_name)
            try:
                with open(file_path, 'rb') as f:
                    template = Template(f.read())
            except:
                continue
            contents.append({'name': template.name,
                             'description': template.description,
                             'singleton': template.singleton,
                             'mount': template.mount,
                             'variables': template.variables,
                             'filename': file_name})

        return contents
