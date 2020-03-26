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
import random
import string

from django.conf import settings
from restless.dj import DjangoResource
from restless.exceptions import NotFound, BadRequest, Conflict

from .models import APIToken
from .forms import CreateServiceForm
from .utils.template import Template
from .utils.kubernetes import KubernetesClient
from .utils.docker import DockerClient


NAMESPACE_TEMPLATE = '''
apiVersion: v1
kind: Namespace
metadata:
  name: $NAME
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ${NAME}-role
  namespace: $NAME
rules:
- apiGroups: ["", "extensions", "apps"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["batch"]
  resources:
  - jobs
  - cronjobs
  verbs: ["*"]
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ${NAME}-binding
  namespace: $NAME
subjects:
- kind: ServiceAccount
  name: default
  namespace: $NAME
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ${NAME}-role
---
kind: Template
name: Namespace
variables:
- name: NAME
  default: user
'''

class APIResource(DjangoResource):
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

        if not api_token.user.is_active:
            return False
        self.request.user = api_token.user
        return True

class ServiceResource(APIResource):
    http_methods = {'list': {'GET': 'list',
                             'POST': 'create'},
                    'detail': {'DELETE': 'delete'}}

    def list(self):
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.request.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_database = []
        for file_name in os.listdir(service_database_path):
            if file_name.endswith('.yaml'):
                service_database.append(file_name[:-5])

        contents = []
        for service in kubernetes_client.list_services(namespace=self.request.user.namespace, label_selector=''):
            name = service.metadata.name
            # ports = [str(p.port) for p in service.spec.ports if p.protocol == 'TCP']
            contents.append({'name': name,
                             'url': 'http://%s-%s.%s' % (name, self.request.user.username, settings.INGRESS_DOMAIN),
                             'created': service.metadata.creation_timestamp,
                             'actions': True if name in service_database else False})

        return contents

    def create(self):
        file_name = self.data.pop('filename')
        if not file_name:
            raise BadRequest()
        service_yaml = os.path.join(settings.SERVICE_TEMPLATE_DIR, file_name)
        try:
            with open(service_yaml, 'rb') as f:
                template = Template(f.read())
        except:
            raise NotFound()

        form = CreateServiceForm(self.data, variables=template.variables)
        if not form.is_valid():
            raise BadRequest()

        for variable in template.variables:
            name = variable['name']
            if name.upper() in ('NAMESPACE', 'HOSTNAME', 'REGISTRY', 'LOCAL', 'REMOTE', 'SHARED'): # Set here later on.
                continue
            setattr(template, name, form.cleaned_data[name])

        kubernetes_client = KubernetesClient()
        if template.singleton and len(kubernetes_client.list_services(namespace=self.request.user.namespace,
                                                                      label_selector='karvdash-template=%s' % template.label)):
            raise Conflict()

        # Resolve naming conflicts.
        name = template.NAME
        names = [service.metadata.name for service in kubernetes_client.list_services(namespace=self.request.user.namespace, label_selector='')]
        while name in names:
            name = form.cleaned_data['NAME'] + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])

        # Set name, hostname, registry, and storage paths.
        template.NAMESPACE = self.request.user.namespace
        template.NAME = name
        template.HOSTNAME = '%s-%s.%s' % (name, self.request.user.username, settings.INGRESS_DOMAIN)
        template.REGISTRY = DockerClient(settings.DOCKER_REGISTRY).registry_host
        template.LOCAL = settings.DATA_DOMAINS['local']['dir'].rstrip('/')
        template.REMOTE = settings.DATA_DOMAINS['remote']['dir'].rstrip('/')
        template.SHARED = settings.DATA_DOMAINS['shared']['dir'].rstrip('/')

        # Inject data folders.
        if template.mount:
            volumes = {}
            for domain, variables in settings.DATA_DOMAINS.items():
                if not variables['dir'] or not variables['host_dir']:
                    continue
                user_path = os.path.join(variables['host_dir'], self.request.user.username)
                if not os.path.exists(user_path):
                    os.makedirs(user_path)
                volumes[domain] = variables.copy()
                volumes[domain]['host_dir'] = user_path
            template.inject_hostpath_volumes(volumes)

        # Add name label.
        template.inject_service_label()

        # Add authentication.
        template.inject_ingress_auth('karvdash-auth', 'Authentication Required - %s' % settings.DASHBOARD_TITLE, redirect_ssl=settings.SERVICE_REDIRECT_SSL)

        # Save yaml.
        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.request.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)
        service_yaml = os.path.join(service_database_path, '%s.yaml' % name)
        with open(service_yaml, 'wb') as f:
            f.write(template.yaml.encode())

        # Apply.
        try:
            if self.request.user.namespace not in [n.metadata.name for n in kubernetes_client.list_namespaces()]:
                template = Template(NAMESPACE_TEMPLATE)
                template.NAME = self.request.user.namespace

                namespace_yaml = os.path.join(settings.SERVICE_DATABASE_DIR, '%s.yaml' % self.request.user.username)
                with open(namespace_yaml, 'wb') as f:
                    f.write(template.yaml.encode())

                kubernetes_client.apply_yaml(namespace_yaml)
            self.request.user.update_kubernetes_secret(kubernetes_client=kubernetes_client)
            kubernetes_client.apply_yaml(service_yaml, namespace=self.request.user.namespace)
        except:
            raise

        return {'name': name,
                'url': 'http://%s-%s.%s' % (name, self.request.user.username, settings.INGRESS_DOMAIN),
                # 'created': creation_timestamp,
                'actions': True}

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
                kubernetes_client.delete_yaml(service_yaml, namespace=self.request.user.namespace)
            except:
                raise
            else:
                os.unlink(service_yaml)

class TemplateResource(APIResource):
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
