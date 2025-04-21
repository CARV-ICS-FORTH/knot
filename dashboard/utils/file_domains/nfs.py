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

from urllib.parse import urlparse
from jinja2 import Template

from .file import FileDomainPrivate, FileDomainShared, FileDomainAdmin
from ..kubernetes import KubernetesClient


NFS_VOLUME_TEMPLATE = '''
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: {{ name }}
spec:
  storageClassName: ""
  volumeName: {{ name }}-pv
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 1Pi
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ name }}-pv
spec:
  accessModes:
    - ReadWriteMany
  capacity:
    storage: 1Pi
  mountOptions:
    - nfsvers=4.1
  csi:
    driver: nfs.csi.k8s.io
    readOnly: false
    volumeHandle: {{ name }}
    volumeAttributes:
      server: {{ server }}
      share: {{ path }}
'''

class NFSVolumeMixin(object):
    def create_volume(self):
        # Create persistent volume and claim.
        kubernetes_client = KubernetesClient()
        volume_names = [pvc.metadata.name for pvc in kubernetes_client.list_persistent_volume_claims(namespace=self._user.namespace)]
        if self.volume_name in volume_names:
            return

        template = Template(NFS_VOLUME_TEMPLATE).render(name=self.volume_name,
                                                        server=urlparse(self.url).hostname,
                                                        path=urlparse(self.url).path)
        kubernetes_client.apply_yaml_data(template.encode(), namespace=self._user.namespace)

    def delete_volume(self):
        kubernetes_client = KubernetesClient()

        # Delete anyway, as the namespace may already be deleted.
        template = Template(NFS_VOLUME_TEMPLATE).render(name=self.volume_name,
                                                        server=urlparse(self.url).hostname,
                                                        path=urlparse(self.url).path)
        kubernetes_client.delete_yaml_data(template.encode(), namespace=self._user.namespace)

class PrivateNFSDomain(FileDomainPrivate, NFSVolumeMixin):
    @property
    def url(self):
        return 'nfs://%s%s' % (self._url.hostname, os.path.join(self._url.path, 'private', self._user.username))

class SharedNFSDomain(FileDomainShared, NFSVolumeMixin):
    @property
    def url(self):
        return 'nfs://%s%s' % (self._url.hostname, os.path.join(self._url.path, 'shared'))

class AdminNFSDomain(FileDomainAdmin, NFSVolumeMixin):
    @property
    def url(self):
        return 'nfs://%s%s' % (self._url.hostname, os.path.join(self._url.path, 'admin'))
