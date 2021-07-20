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
import json
import yaml
import re
import kubernetes

from django.conf import settings
from restless.dj import DjangoResource
from restless.exceptions import NotFound, BadRequest, Conflict, Forbidden, TooManyRequests
from urllib.parse import urlparse

from .models import APIToken, User
from .forms import CreateServiceForm, CreateDatasetForm
from .datasets import LOCAL_S3_DATASET_TEMPLATE, REMOTE_S3_DATASET_TEMPLATE, LOCAL_H3_DATASET_TEMPLATE, REMOTE_H3_DATASET_TEMPLATE, ARCHIVE_DATASET_TEMPLATE
from .utils.template import Template, ServiceTemplate, FileTemplate
from .utils.kubernetes import KubernetesClient
from .utils.docker import DockerClient
from .utils.base64 import base64_encode, base64_decode


SERVICE_TEMPLATE_TEMPLATE = '''
apiVersion: karvdash.carv.ics.forth.gr/v1
kind: Template
metadata:
  name: $NAME
spec:
  data: $DATA
---
kind: Template
name: ServiceTemplate
variables:
- name: NAME
  default: template
- name: DATA
  default: ""
'''

class APIResource(DjangoResource):
    # def is_debug(self):
    #     return True

    # def bubble_exceptions(self):
    #     return True

    @property
    def user(self):
        if getattr(self.request.user, 'is_impersonate', False):
            return User.objects.get(pk=self.request.user.pk)
        return self.request.user

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
                    'detail': {'POST': 'execute',
                               'DELETE': 'delete'}}

    def get_template(self, identifier):
        template_resource = TemplateResource()
        template_resource.request = self.request
        return template_resource.get_template(identifier)

    def list(self):
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_database = []
        for file_name in os.listdir(service_database_path):
            if file_name.endswith('.yaml'):
                service_database.append(file_name[:-5])

        ingress_url = urlparse(settings.INGRESS_URL)

        contents = []
        ingresses = kubernetes_client.list_ingresses(namespace=self.user.namespace)
        for service in kubernetes_client.list_services(namespace=self.user.namespace, label_selector='karvdash-template'):
            name = service.metadata.name
            url = None
            for ingress in ingresses:
                if name == ingress.metadata.name:
                    try:
                        url = '%s://%s' % (ingress_url.scheme, ingress.spec.rules[0].host)
                    except:
                        pass
                    break
            try:
                service_template = self.get_template(service.metadata.labels['karvdash-template']).format()
            except:
                service_template = None
            if service_template:
                try:
                    values = service.metadata.annotations['karvdash-values']
                    service_template['values'] = json.loads(values)
                except:
                    pass
            contents.append({'name': name,
                             'url': url,
                             'created': service.metadata.creation_timestamp,
                             'actions': True if name in service_database else False,
                             'template': service_template})

        return contents

    def create(self):
        # Backwards compatibility.
        filename = self.data.pop('filename', None)
        if filename:
            identifier = filename + '.template.yaml'
        else:
            try:
                identifier = self.data.pop('id')
            except:
                raise BadRequest()

        template = self.get_template(identifier)
        if not template:
            raise NotFound()

        form = CreateServiceForm(self.data, variables=template.variables)
        if not form.is_valid():
            raise BadRequest()

        for variable in template.variables:
            name = variable['name']
            # Backwards compatibility ("PRIVATE" and "SHARED").
            if name.upper() in ('NAMESPACE', 'HOSTNAME', 'REGISTRY', 'PRIVATE', 'PRIVATE_DIR', 'PRIVATE_VOLUME', 'SHARED', 'SHARED_DIR', 'SHARED_VOLUME'): # Set here later on.
                continue
            if name in self.data:
                setattr(template, name, form.cleaned_data[name])

        kubernetes_client = KubernetesClient()
        if template.singleton and len(kubernetes_client.list_services(namespace=self.user.namespace,
                                                                      label_selector='karvdash-template=%s' % template.identifier)):
            raise Conflict()

        # Resolve naming conflicts.
        name = template.NAME
        names = [service.metadata.name for service in kubernetes_client.list_services(namespace=self.user.namespace, label_selector='')]
        while name in names:
            name = form.cleaned_data['NAME'] + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])

        # Generate service URLs.
        if settings.GENERATE_SERVICE_URLS:
            prefix = '%s-%s' % (name, self.user.username)
        else:
            # XXX Non-atomic prefix selection.
            used_prefixes = []
            for ingress in kubernetes_client.list_ingresses(namespace=''):
                try:
                    used_prefixes.append(ingress.spec.rules[0].host.split('.', 1)[0])
                except:
                    pass
            available_prefixes = list(set(settings.SERVICE_URL_PREFIXES) - set(used_prefixes))
            if not available_prefixes:
                raise TooManyRequests()
            prefix = random.choice(available_prefixes)

        ingress_url = urlparse(settings.INGRESS_URL)
        ingress_host = '%s:%s' % (ingress_url.hostname, ingress_url.port) if ingress_url.port else ingress_url.hostname

        # Set namespace, name, hostname, registry, and storage paths.
        template.NAMESPACE = self.user.namespace
        template.NAME = name
        template.HOSTNAME = '%s.%s' % (prefix, ingress_host)
        template.REGISTRY = DockerClient(settings.DOCKER_REGISTRY_URL, settings.DOCKER_REGISTRY_CERT_FILE).registry_host if settings.DOCKER_REGISTRY_URL else ''
        template.PRIVATE = self.user.file_domains['private'].mount_dir # Backwards compatibility.
        template.PRIVATE_DIR = self.user.file_domains['private'].mount_dir
        template.PRIVATE_VOLUME = self.user.file_domains['private'].volume_name
        template.SHARED = self.user.file_domains['shared'].mount_dir # Backwards compatibility.
        template.SHARED_DIR = self.user.file_domains['shared'].mount_dir
        template.SHARED_VOLUME = self.user.file_domains['private'].volume_name

        # Add template label and values.
        template.inject_service_details()

        # Add authentication.
        if template.auth:
            template.inject_ingress_auth('karvdash-auth', 'Authentication Required - %s' % settings.DASHBOARD_TITLE, redirect_ssl=(ingress_url.scheme == 'https'))

        # Add no local datasets label.
        if not template.datasets:
            template.inject_no_datasets_label()

        # Inject data folders.
        # if settings.DEBUG:
        #     template.inject_volumes(self.user.file_domains, add_api_settings=True)
        #     template.inject_volumes(self.user.dataset_volumes, is_datasets=True)

        # Save yaml.
        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)
        service_yaml = os.path.join(service_database_path, '%s.yaml' % name)
        with open(service_yaml, 'wb') as f:
            f.write(template.yaml.encode())

        # Apply.
        self.user.update_kubernetes_credentials(kubernetes_client=kubernetes_client)
        kubernetes_client.apply_yaml_file(service_yaml, namespace=self.user.namespace)

        service_template = template.format()
        service_template['values'] = template.values
        return {'name': name,
                'url': '%s://%s.%s' % (ingress_url.scheme, prefix, ingress_host),
                # 'created': creation_timestamp,
                'actions': True,
                'template': service_template}

    def execute(self, pk):
        name = pk

        if 'command' not in self.data:
            raise BadRequest()
        all_pods = True if self.data.get('all_pods') in (1, '1', 'True', 'true') else False

        result = KubernetesClient().exec_command_in_pod(namespace=self.user.namespace,
                                                        label_selector='app=%s' % name,
                                                        command=self.data['command'],
                                                        all_pods=all_pods)
        return {'result': result}

    def delete(self, pk):
        name = pk
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_yaml = os.path.join(service_database_path, '%s.yaml' % name)
        if not os.path.exists(service_yaml):
            raise NotFound()
        else:
            try:
                kubernetes_client.delete_yaml_file(service_yaml, namespace=self.user.namespace)
            except:
                raise
            else:
                os.unlink(service_yaml)

class TemplateResource(APIResource):
    http_methods = {'list': {'GET': 'list',
                             'POST': 'add'},
                    'detail': {'GET': 'get',
                               'DELETE': 'remove'}}

    def get_template(self, identifier):
        for template in self.templates:
            if template.identifier == identifier:
                return template
        return None

    @property
    def templates(self):
        contents = []
        for file_name in os.listdir(settings.SYSTEM_TEMPLATE_DIR):
            if not file_name.endswith('.template.yaml'):
                continue
            if os.path.exists(os.path.join(settings.SERVICE_TEMPLATE_DIR, file_name)):
                continue
            if file_name in settings.DISABLED_SERVICE_TEMPLATES:
                continue

            try:
                template = FileTemplate(os.path.join(settings.SYSTEM_TEMPLATE_DIR, file_name))
            except:
                continue
            contents.append(template)
        if os.path.exists(settings.SERVICE_TEMPLATE_DIR):
            for file_name in os.listdir(settings.SERVICE_TEMPLATE_DIR):
                if not file_name.endswith('.template.yaml'):
                    continue

                try:
                    template = FileTemplate(os.path.join(settings.SERVICE_TEMPLATE_DIR, file_name))
                except:
                    continue
                contents.append(template)

        kubernetes_client = KubernetesClient()
        try:
            service_templates = kubernetes_client.list_crds(group='karvdash.carv.ics.forth.gr', version='v1', namespace=self.user.namespace, plural='templates')
            for service_template in service_templates:
                try:
                    template = ServiceTemplate(base64_decode(service_template['spec']['data']), identifier=service_template['metadata']['name'])
                except:
                    continue
                contents.append(template)
        except:
            pass

        return contents

    def list(self):
        return [dict(template.format(), custom=(not isinstance(template, FileTemplate))) for template in self.templates]

    def add(self):
        try:
            data = self.data.pop('data')
            template = ServiceTemplate(data)
        except:
            raise BadRequest()

        identifier = re.sub(r'[^A-Za-z0-9 ]+', '', template.name.lower())
        identifiers = [template.identifier for template in self.templates]
        while True:
            identifier = identifier.replace(' ', '-') + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])
            if identifier not in identifiers:
                template.identifier = identifier
                break

        service_template = Template(SERVICE_TEMPLATE_TEMPLATE)
        service_template.NAME = template.identifier
        service_template.DATA = base64_encode(data)

        kubernetes_client = KubernetesClient()
        kubernetes_client.apply_crd(group='karvdash.carv.ics.forth.gr', version='v1', namespace=self.user.namespace, plural='templates', yaml=yaml.load(service_template.yaml, Loader=yaml.FullLoader))

        return template.format()

    def get(self, pk):
        identifier = pk

        template = self.get_template(identifier)
        if not template:
            raise NotFound()

        return template.format(include_data=True)

    def remove(self, pk):
        identifier = pk

        template = self.get_template(identifier)
        if not template:
            raise NotFound()

        if type(template) == FileTemplate:
            raise Forbidden()
        kubernetes_client = KubernetesClient()
        kubernetes_client.delete_crd(group='karvdash.carv.ics.forth.gr', version='v1', namespace=self.user.namespace, plural='templates', name=template.identifier)

class DatasetResource(APIResource):
    http_methods = {'list': {'GET': 'list',
                             'POST': 'add'},
                    'detail': {'POST': 'edit',
                               'DELETE': 'remove'}}

    @property
    def dataset_templates(self):
        templates = [ServiceTemplate(LOCAL_S3_DATASET_TEMPLATE, identifier='s3-local'),
                     ServiceTemplate(REMOTE_S3_DATASET_TEMPLATE, identifier='s3-remote'),
                     ServiceTemplate(LOCAL_H3_DATASET_TEMPLATE, identifier='h3-local'),
                     ServiceTemplate(REMOTE_H3_DATASET_TEMPLATE, identifier='h3-remote'),
                     ServiceTemplate(ARCHIVE_DATASET_TEMPLATE, identifier='archive')]
        return [t for t in templates if t.identifier not in settings.DISABLED_DATASET_TEMPLATES]

    def get_template(self, dataset_type):
        dataset_templates = {'COS': Template(REMOTE_S3_DATASET_TEMPLATE),
                             'H3': Template(REMOTE_H3_DATASET_TEMPLATE),
                             'ARCHIVE': Template(ARCHIVE_DATASET_TEMPLATE)}
        return dataset_templates[dataset_type]

    def get_dataset(self, name):
        for dataset in self.datasets:
            if dataset['name'] == name:
                return dataset
        return None

    @property
    def datasets(self):
        contents = []
        kubernetes_client = KubernetesClient()
        for dataset in kubernetes_client.list_crds(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self.user.namespace, plural='datasets'):
            try:
                if dataset['metadata']['labels']['karvdash-hidden'] == 'true':
                    continue
            except:
                pass
            try:
                dataset_type = dataset['spec']['local']['type']
                if dataset_type in ('COS', 'H3', 'ARCHIVE'):
                    contents.append({'name': dataset['metadata']['name'], **dataset['spec']['local']})
            except:
                continue

        return contents

    def list(self):
        return self.datasets

    def add(self, template):
        form = CreateDatasetForm(self.data, variables=template.variables)
        if not form.is_valid():
            raise BadRequest()

        for variable in template.variables:
            name = variable['name']
            if name in self.data:
                setattr(template, name, form.cleaned_data[name])
        if 'REGION' in [v['name'].upper() for v in template.variables]:
            if not template.REGION:
                template.REGION = '""'

        # Resolve naming conflicts.
        name = template.NAME
        names = [dataset['name'] for dataset in self.datasets]
        while name in names:
            name = form.cleaned_data['NAME'] + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])

        # Set namespace and name.
        template.NAMESPACE = self.user.namespace
        template.NAME = name

        kubernetes_client = KubernetesClient()
        try:
            kubernetes_client.apply_crd(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self.user.namespace, plural='datasets', yaml=yaml.load(template.yaml, Loader=yaml.FullLoader))
        except kubernetes.client.rest.ApiException as e:
            try:
                message = json.loads(e.body)['message']
            except:
                message = str(e)
            raise Exception(message)

        return {'name': name}

    def edit(self, pk):
        pass

    def remove(self, pk):
        name = pk

        dataset = self.get_dataset(name)
        if not dataset:
            raise NotFound()

        kubernetes_client = KubernetesClient()
        kubernetes_client.delete_crd(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self.user.namespace, plural='datasets', name=name)
