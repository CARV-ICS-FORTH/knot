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

from django.db import models
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.signals import user_logged_in
from django.contrib import messages
from django.dispatch import receiver
from django.conf import settings
from urllib.parse import urlparse
from collections import namedtuple
from jinja2 import Template

from .utils.kubernetes import KubernetesClient
from .utils.file_domains.file import PrivateFileDomain, SharedFileDomain
from .utils.file_domains.nfs import PrivateNFSDomain, SharedNFSDomain
from .utils.harbor import HarborClient


NAMESPACE_TEMPLATE = '''
apiVersion: v1
kind: Namespace
metadata:
  name: {{ name }}
  labels:
    karvdash: enabled
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: admin-binding
  namespace: {{ name }}
subjects:
- kind: ServiceAccount
  name: default
  namespace: {{ name }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
'''

ARGO_SERVICE_ACCOUNT_TEMPLATE = '''
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    workflows.argoproj.io/rbac-rule: "sub == '{{ name }}'"
    workflows.argoproj.io/rbac-rule-precedence: "1"
  name: {{ argo_service_account }}
  namespace: {{ argo_namespace }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: argo-binding
  namespace: {{ namespace }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: {{ argo_service_account }}
  namespace: {{ argo_namespace }}
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
                if hasattr(user, 'ldap_user'):
                    # Users coming from LDAP have unusable passwords.
                    continue
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
                    if 'karvdash-hidden' in dataset['metadata']['labels'].keys():
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

    def update_registry_credentials(self, kubernetes_client=None):
        if not settings.HARBOR_URL or not settings.HARBOR_ADMIN_PASSWORD:
            return

        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()

        ingress_url = urlparse(settings.INGRESS_URL)
        ingress_host = '%s:%s' % (ingress_url.hostname, ingress_url.port) if ingress_url.port else ingress_url.hostname

        harbor_client = HarborClient(settings.HARBOR_URL, settings.HARBOR_ADMIN_PASSWORD)
        harbor_cli_url = harbor_client.get_cli_url(self)
        if not harbor_cli_url:
            return
        kubernetes_client.update_registry_secret(self.namespace, harbor_cli_url, '%s@%s' % (self.username, ingress_host))

        # Add user to public project as developer.
        harbor_client.add_user_to_project(self, 'library', HarborClient.ROLE_DEVELOPER, public=True)

        # Create private project.
        harbor_client.add_user_to_project(self, self.username, HarborClient.ROLE_ADMIN, public=False)

    def create_namespace(self, request):
        kubernetes_client = KubernetesClient()

        # Create namespace.
        if self.namespace not in [n.metadata.name for n in kubernetes_client.list_namespaces()]:
            namespace_template = Template(NAMESPACE_TEMPLATE).render(name=self.namespace)
            kubernetes_client.apply_yaml_data(namespace_template.encode())

        # Create or update registry secret.
        self.update_registry_credentials(kubernetes_client)

        # Create volumes.
        for name, domain in self.file_domains.items():
            domain.create_domain()

        # Create directory for notebooks.
        if settings.JUPYTERHUB_NOTEBOOK_DIR:
            path_worker = self.file_domains['private'].path_worker([])
            notebook_dir = settings.JUPYTERHUB_NOTEBOOK_DIR.strip('/')
            if not path_worker.exists(notebook_dir):
                path_worker.mkdir(notebook_dir)
            try:
                path_worker.chown(notebook_dir, 1000, 1000) # XXX Hardcoded for JupyterHub (won't work locally).
            except:
                pass

        # Create service account for Argo.
        if settings.ARGO_WORKFLOWS_NAMESPACE:
            argo_service_account_name = self.namespace
            if argo_service_account_name not in [s.metadata.name for s in kubernetes_client.list_service_accounts(settings.ARGO_WORKFLOWS_NAMESPACE)]:
                argo_template = Template(ARGO_SERVICE_ACCOUNT_TEMPLATE).render(name=self.username,
                                                                               namespace=self.namespace,
                                                                               argo_service_account=argo_service_account_name,
                                                                               argo_namespace=settings.ARGO_WORKFLOWS_NAMESPACE)
                kubernetes_client.apply_yaml_data(argo_template.encode())

    def delete_namespace(self):
        kubernetes_client = KubernetesClient()

        # Delete service account for Argo.
        if settings.ARGO_WORKFLOWS_NAMESPACE:
            argo_service_account_name = self.namespace
            argo_template = Template(ARGO_SERVICE_ACCOUNT_TEMPLATE).render(name=self.username,
                                                                           namespace=self.namespace,
                                                                           argo_service_account=argo_service_account_name,
                                                                           argo_namespace=settings.ARGO_WORKFLOWS_NAMESPACE)
            kubernetes_client.delete_yaml_data(argo_template.encode())

        # Delete namespace.
        namespace_template = Template(NAMESPACE_TEMPLATE).render(name=self.namespace)
        kubernetes_client.delete_yaml_data(namespace_template.encode())

        # Delete volumes.
        for name, domain in self.file_domains.items():
            domain.delete_domain()

def generate_token():
    return ''.join(random.choice('0123456789abcdef') for n in range(40))

class Message(models.Model):
    user = models.ForeignKey(User, related_name='messages', on_delete=models.CASCADE)
    level = models.CharField(max_length=8, choices=[(k.lower(), k.lower()) for k in messages.DEFAULT_LEVELS.keys()], blank=False, null=False)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def add(cls, request, level, message):
        cls.objects.create(user=request.user, level=level, message=message)
        messages.add_message(request, messages.DEFAULT_LEVELS[level.upper()], message)

    @property
    def label(self):
        if self.level == 'debug':
            return 'secondary'
        if self.level == 'error':
            return 'danger'
        return self.level

@receiver(user_logged_in)
def create_user_namespace(sender, user, request, **kwargs):
    user = User.objects.get(pk=user.pk)
    user.create_namespace(request) # Make sure namespace and volumes are created on upgrade
