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

from django.db import models
from django.contrib.auth.models import User as AuthUser, update_last_login
from django.contrib.auth.signals import user_logged_in
from django.contrib import messages
from django.dispatch import receiver
from django.conf import settings
from urllib.parse import urlparse
from jinja2 import Template
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from impersonate.signals import session_begin

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
    knot: enabled
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
apiVersion: v1
kind: Secret
metadata:
  name: {{ argo_service_account }}.service-account-token
  annotations:
    kubernetes.io/service-account.name: {{ argo_service_account }}
  namespace: {{ argo_namespace }}
type: kubernetes.io/service-account-token
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
            for user in cls.objects.filter(is_active=True).exclude(profile__is_team=True):
                if hasattr(user, 'ldap_user'):
                    # Users coming from LDAP have unusable passwords.
                    continue
                f.write('%s:$%s\n' % (user.username, user.password))

    @property
    def namespace(self):
        return 'knot-%s' % self.username

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
    def local_data(self):
        data = {'username': self.username,
                'namespace': self.namespace,
                'ingress_url': settings.INGRESS_URL,
                'private_dir': self.file_domains['private'].mount_dir,
                'private_volume': self.file_domains['private'].volume_name,
                'shared_dir': self.file_domains['shared'].mount_dir,
                'shared_volume': self.file_domains['private'].volume_name}
        if settings.ARGO_WORKFLOWS_URL:
            data.update({'argo_workflows_url': settings.ARGO_WORKFLOWS_URL})
        if settings.HARBOR_URL:
            data.update({'private_registry_url': '%s/%s' % (settings.HARBOR_URL, self.username),
                         'shared_registry_url': '%s/%s' % (settings.HARBOR_URL, 'library'),
                         'private_repo_url': '%s/chartrepo/%s' % (settings.HARBOR_URL, self.username),
                         'shared_repo_url': '%s/chartrepo/%s' % (settings.HARBOR_URL, 'library')})
        return data

    def send_update(self, message):
        channel_layer = get_channel_layer()
        group_name = 'updates_%s' % self.username
        async_to_sync(channel_layer.group_send)(group_name, {'type': 'update_message', 'message': message})

    def update_kubernetes_credentials(self, kubernetes_client=None):
        if settings.VOUCH_URL:
            return

        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()
        kubernetes_client.update_secret(self.namespace, 'knot-auth', [self.literal_auth])

    def delete_kubernetes_credentials(self, kubernetes_client=None):
        if settings.VOUCH_URL:
            return

        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()
        kubernetes_client.delete_secret(self.namespace, 'knot-auth')

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
            if (argo_service_account_name not in [s.metadata.name for s in kubernetes_client.list_service_accounts(settings.ARGO_WORKFLOWS_NAMESPACE)] or
                ("%s.service-account-token" % argo_service_account_name) not in [s.metadata.name for s in kubernetes_client.list_secrets(settings.ARGO_WORKFLOWS_NAMESPACE)]):
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

class Profile(models.Model):
    user = models.OneToOneField(AuthUser, primary_key=True, related_name='profile', on_delete=models.CASCADE)
    is_team = models.BooleanField(blank=False, null=False, default=False)
    description = models.CharField(max_length=128, blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

class Membership(models.Model):
    user = models.ForeignKey(User, related_name='memberships', on_delete=models.CASCADE)
    team = models.ForeignKey(User, related_name='members', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

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

class Task(models.Model):
    user = models.ForeignKey(User, related_name='tasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=32, blank=False, null=False)
    task_id = models.CharField(max_length=36, blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def add(cls, user, name, task_id):
        cls.objects.create(user=user, name=name, task_id=task_id)

@receiver(user_logged_in)
def create_user_namespace(sender, user, request, **kwargs):
    user = User.objects.get(pk=user.pk)
    if not user.last_login:
        update_last_login(sender, user, **kwargs) # The first time, this handler may be called first
    user.create_namespace(request) # Make sure namespace and volumes are created on upgrade

@receiver(session_begin)
def impersonate(sender, impersonating, request, **kwargs):
    create_user_namespace(sender, impersonating, request, **kwargs)
