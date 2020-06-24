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
from django.dispatch import receiver
from django.conf import settings


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
    def volumes(self):
        volumes = {}
        for domain, variables in settings.FILE_DOMAINS.items():
            if not variables['dir'] or not variables['host_dir']:
                continue
            if variables.get('mode') == 'shared':
                user_path = variables['host_dir']
            else:
                user_path = os.path.join(variables['host_dir'], self.username)
            if not os.path.exists(user_path):
                os.makedirs(user_path)
            volumes[domain] = variables.copy()
            volumes[domain]['host_dir'] = user_path
        return volumes

    @property
    def api_token(self):
        try:
            api_token = APIToken.objects.get(user=self)
        except APIToken.DoesNotExist:
            api_token = APIToken(user=self)
            api_token.save()
        return api_token

    def update_kubernetes_credentials(self, kubernetes_client=None):
        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()
        kubernetes_client.update_secret(self.namespace, 'karvdash-auth', self.literal_auth)

    def delete_kubernetes_credentials(self, kubernetes_client=None):
        from .utils.kubernetes import KubernetesClient

        if not kubernetes_client:
            kubernetes_client = KubernetesClient()
        kubernetes_client.delete_secret(self.namespace, 'karvdash-auth')

def generate_token():
    return ''.join(random.choice('0123456789abcdef') for n in range(40))

class APIToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    token = models.CharField(max_length=64, blank=False, null=False, default=generate_token)

@receiver(user_logged_in)
def create_api_token(sender, user, request, **kwargs):
    _ = User.objects.get(pk=user.pk).api_token # Get or create
