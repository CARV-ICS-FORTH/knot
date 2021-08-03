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
import socket
import shutil
import random

from django.db import models
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings
from urllib.parse import urlparse
from collections import namedtuple

from .utils.template import Template
from .utils.kubernetes import KubernetesClient
from .utils.file_domains.file import PrivateFileDomain, SharedFileDomain
from .utils.file_domains.nfs import PrivateNFSDomain, SharedNFSDomain


NAMESPACE_TEMPLATE = '''
apiVersion: v1
kind: Namespace
metadata:
  name: $NAME
  labels:
    karvdash: enabled
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: admin-binding
  namespace: $NAME
subjects:
- kind: ServiceAccount
  name: default
  namespace: $NAME
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
---
kind: Template
name: Namespace
variables:
- name: NAME
  default: user
'''

TOKEN_CONFIG_MAP_TEMPLATE = '''
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${NAME}
data:
  config.ini: |
    [Karvdash]
    base_url = $BASE_URL
    token = $TOKEN
---
kind: Template
name: TokenConfigMap
variables:
- name: NAME
  default: user
- name: BASE_URL
  default: http://karvdash.default.svc/api
- name: TOKEN
  default: ""
'''

ARGO_SERVICE_ACCOUNT_TEMPLATE = '''
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    workflows.argoproj.io/rbac-rule: "sub == '${NAME}'"
    workflows.argoproj.io/rbac-rule-precedence: "1"
  name: ${ARGO_SERVICE_ACCOUNT}
  namespace: ${ARGO_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: argo-binding
  namespace: ${NAMESPACE}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: ${ARGO_SERVICE_ACCOUNT}
  namespace: ${ARGO_NAMESPACE}
---
kind: Template
name: ArgoServiceAccount
variables:
- name: NAME
  default: user
- name: NAMESPACE
  default: namespace
- name: ARGO_SERVICE_ACCOUNT
  default: karvdash-user
- name: ARGO_NAMESPACE
  default: argo
'''

class User(AuthUser):
    class Meta:
        proxy = True

    @classmethod
    def export_to_htpasswd(cls, htpasswd_dir):
        if not htpasswd_dir:
            return
        with open(os.path.join(htpasswd_dir, 'htpasswd'), 'w') as f:
            for user in cls.objects.filter(is_active=True):
                f.write('%s:$%s\n' % (user.username, user.password))

    @property
    def namespace(self):
        return 'karvdash-%s' % self.username

    @property
    def literal_auth(self):
        return 'auth=%s:$%s\n' % (self.username, self.password)

    @property
    def file_domains(self):
        files_url = urlparse(settings.FILES_URL)
        if files_url.scheme == 'file':
            return {'private': PrivateFileDomain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self),
                    'shared': SharedFileDomain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self)}
        if files_url.scheme == 'nfs':
            return {'private': PrivateNFSDomain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self),
                    'shared': SharedNFSDomain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self)}
        raise ValueError('Unsupported URL for files')

    @property
    def dataset_volumes(self):
        # Return datasets as objects.
        DatasetTuple = namedtuple('DatasetTuple', ['volume_name', 'url', 'mount_dir'])

        datasets = {}
        kubernetes_client = KubernetesClient()
        try:
            for dataset in kubernetes_client.list_crds(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self.namespace, plural='datasets'):
                try:
                    # Hidden datasets are included in file domains.
                    if dataset['metadata']['labels']['karvdash-hidden'] == 'true':
                        continue
                except:
                    pass
                try:
                    dataset_type = dataset['spec']['local']['type']
                    if dataset_type in ('COS', 'H3', 'ARCHIVE'):
                        dataset_name = dataset['metadata']['name']
                        datasets[dataset_name] = DatasetTuple(dataset_name, 'dataset://%s' % dataset_name, '/mnt/datasets/%s' % dataset_name)
                    else:
                        continue
                except:
                    continue
        except:
            pass

        return datasets

    @property
    def api_token(self):
        try:
            api_token = APIToken.objects.get(user=self)
        except APIToken.DoesNotExist:
            api_token = APIToken(user=self)
            api_token.save()
        return api_token

    def update_kubernetes_credentials(self, kubernetes_client=None):
        if settings.VOUCH_URL:
            return

        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()
        kubernetes_client.update_secret(self.namespace, 'karvdash-auth', [self.literal_auth])

    def delete_kubernetes_credentials(self, kubernetes_client=None):
        if settings.VOUCH_URL:
            return

        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()
        kubernetes_client.delete_secret(self.namespace, 'karvdash-auth')

    def create_namespace(self, request):
        ingress_url = urlparse(settings.INGRESS_URL)
        ingress_host = '%s:%s' % (ingress_url.hostname, ingress_url.port) if ingress_url.port else ingress_url.hostname

        # Create service directory.
        if not os.path.exists(settings.SERVICE_DATABASE_DIR):
            os.makedirs(settings.SERVICE_DATABASE_DIR)

        kubernetes_client = KubernetesClient()

        # Create namespace.
        if self.namespace not in [n.metadata.name for n in kubernetes_client.list_namespaces()]:
            namespace_template = Template(NAMESPACE_TEMPLATE)
            namespace_template.NAME = self.namespace
            kubernetes_client.apply_yaml_data(namespace_template.yaml.encode())

        # Create API connectivity configuration (mounted inside containers).
        api_config_map_name = 'karvdash-api'
        if api_config_map_name not in [c.metadata.name for c in kubernetes_client.list_config_maps(self.namespace)]:
            service_domain = settings.SERVICE_DOMAIN
            if not service_domain:
                # If running in Kubernetes this should be set.
                service_host = socket.gethostbyname(socket.gethostname())
                service_port = request.META['SERVER_PORT']
                service_domain = '%s:%s' % (service_host, service_port)
            api_template = Template(TOKEN_CONFIG_MAP_TEMPLATE)
            api_template.NAME = api_config_map_name
            api_template.BASE_URL = 'http://%s/api' % service_domain
            api_template.TOKEN = self.api_token.token # Get or create
            kubernetes_client.apply_yaml_data(api_template.yaml.encode(), namespace=self.namespace)

        # Create registry secret.
        kubernetes_client.create_registry_secret(self.namespace, settings.REGISTRY_URL, 'admin@%s' % ingress_host)

        # Create volumes.
        for name, domain in self.file_domains.items():
            domain.create_domain()

        # Create directory for notebooks.
        if settings.JUPYTERHUB_NOTEBOOK_DIR:
            path_worker = self.file_domains['private'].path_worker([])
            notebook_dir = settings.JUPYTERHUB_NOTEBOOK_DIR.strip('/')
            if not path_worker.exists(notebook_dir):
                path_worker.mkdir(notebook_dir)
            path_worker.chown(notebook_dir, 1000, 1000) # XXX Hardcoded for JupyterHub.

        # Create service account for Argo.
        if settings.ARGO_WORKFLOWS_NAMESPACE:
            argo_service_account_name = self.namespace
            if argo_service_account_name not in [s.metadata.name for s in kubernetes_client.list_service_accounts(settings.ARGO_WORKFLOWS_NAMESPACE)]:
                argo_template = Template(ARGO_SERVICE_ACCOUNT_TEMPLATE)
                argo_template.NAME = self.username
                argo_template.NAMESPACE = self.namespace
                argo_template.ARGO_SERVICE_ACCOUNT = argo_service_account_name
                argo_template.ARGO_NAMESPACE = settings.ARGO_WORKFLOWS_NAMESPACE
                kubernetes_client.apply_yaml_data(argo_template.yaml.encode())

    def delete_namespace(self):
        kubernetes_client = KubernetesClient()

        # Delete service account for Argo.
        if settings.ARGO_WORKFLOWS_NAMESPACE:
            argo_service_account_name = self.namespace
            argo_template = Template(ARGO_SERVICE_ACCOUNT_TEMPLATE)
            argo_template.NAME = self.username
            argo_template.NAMESPACE = self.namespace
            argo_template.ARGO_SERVICE_ACCOUNT = argo_service_account_name
            argo_template.ARGO_NAMESPACE = settings.ARGO_WORKFLOWS_NAMESPACE
            kubernetes_client.delete_yaml_data(argo_template.yaml.encode())

        # Delete service directory.
        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.username)
        if os.path.exists(service_database_path):
            shutil.rmtree(service_database_path)

        # Delete namespace.
        namespace_template = Template(NAMESPACE_TEMPLATE)
        namespace_template.NAME = self.namespace
        kubernetes_client.delete_yaml_data(namespace_template.yaml.encode())

        # Delete volumes.
        for name, domain in self.file_domains.items():
            domain.delete_domain()

def generate_token():
    return ''.join(random.choice('0123456789abcdef') for n in range(40))

class APIToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    token = models.CharField(max_length=64, blank=False, null=False, default=generate_token)

@receiver(user_logged_in)
def create_user_namespace(sender, user, request, **kwargs):
    user = User.objects.get(pk=user.pk)
    user.create_namespace(request) # Make sure namespace and volumes are created on upgrade
