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
import zipfile
import shutil

from urllib.parse import urlparse
from datetime import datetime

from ..kubernetes import KubernetesClient
from ..template import Template


HOSTPATH_VOLUME_TEMPLATE = '''
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: $NAME
spec:
  storageClassName: ""
  volumeName: $NAME-pv
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: $SIZE
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: $NAME-pv
spec:
  accessModes:
    - ReadWriteMany
  capacity:
    storage: $SIZE
  hostPath:
    path: $PATH
---
kind: Template
name: HostpathVolumeTemplate
variables:
- name: NAME
  default: volume
- name: SIZE
  default: 1Pi
- name: PATH
  default: ""
'''

class FileDomainPathWorker(object):
    def __init__(self, domain, path_components):
        self._domain = domain
        self._path_components = path_components

    @property
    def real_path(self):
        tmp_path = os.path.join(self._domain.user_dir, '/'.join(self._path_components)).rstrip('/')
        if not os.path.normpath(tmp_path).startswith(tmp_path):
            raise ValueError('Unsupported path')
        return os.path.normpath(tmp_path)

    def path_of(self, name):
        return os.path.join(self.real_path, name)

    def exists(self, name=None):
        return os.path.exists(self.real_path if not name else self.path_of(name))

    def isfile(self, name=None):
        return os.path.isfile(self.real_path if not name else self.path_of(name))

    def isdir(self, name=None):
        return os.path.isdir(self.real_path if not name else self.path_of(name))

    def open(self, name, mode):
        return open(self.path_of(name), mode)

    def listdir(self):
        listing = []
        real_path = self.real_path
        for name in os.listdir(self.real_path):
            if self.isdir(name):
                file_type = 'dir'
            elif self.isfile(name):
                file_type = 'file'
            else:
                continue
            listing.append({'name': name,
                            'modified': datetime.fromtimestamp(os.path.getmtime(os.path.join(real_path, name))),
                            'type': file_type,
                            'size': os.path.getsize(os.path.join(real_path, name)) if file_type != 'dir' else 0})
        return listing

    def mkdir(self, name):
        os.mkdir(self.path_of(name))

    def rmdir(self, name, recursive=True):
        if not recursive:
            os.rmdir(self.path_of(name))
            return
        shutil.rmtree(self.path_of(name))

    def upload(self, file, name):
        shutil.move(file.name, self.path_of(name))

    def download(self, name, response):
        zip_path = self.path_of(name)
        with zipfile.ZipFile(response, 'w') as zip_file:
            for root, dirs, files in os.walk(zip_path):
                for file in files:
                    zip_add_file = os.path.join(root, file)
                    zip_file.write(zip_add_file, zip_add_file[len(os.path.dirname(zip_path)):])

    def remove(self, name):
        os.remove(self.path_of(name))

class FileDomain(object):
    def __init__(self, url, mount_dir, user):
        if not user:
            raise ValueError('Empty user')

        self._url = urlparse(url)
        self._mount_dir = mount_dir # Local mountpoint from settings
        self._user = user

    def create_user_dir(self):
        if not os.path.exists(self.user_dir):
            os.makedirs(self.user_dir)

    def delete_user_dir(self):
        raise NotImplementedError

    def create_domain(self):
        self.create_user_dir()
        self.create_volume()

    def delete_domain(self):
        self.delete_volume()
        self.delete_user_dir()

    @property
    def name(self):
        ''' How to name the domain when mounting it ("private" or "shared"). '''
        raise NotImplementedError

    @property
    def volume_name(self):
        ''' How to name the volume when mounting it. '''
        return 'karvdash-%s-volume-%s' % (self._user, self.name)

    @property
    def mount_dir(self):
        ''' Where to mount the domain. '''
        return '/%s' % self.name

    @property
    def user_dir(self):
        ''' The user-specific path for the domain (for internal use). '''
        raise NotImplementedError

    @property
    def url(self):
        ''' The URL of the domain to be mounted. '''
        raise NotImplementedError

    def path_worker(self, subpath_components):
        return FileDomainPathWorker(self, subpath_components)

class FileDomainPrivate(FileDomain):
    def delete_user_dir(self):
        if os.path.exists(self.user_dir):
            shutil.rmtree(self.user_dir)

    @property
    def name(self):
        return 'private'

    @property
    def user_dir(self):
        return os.path.join(self._mount_dir, 'private', self._user.username)

class FileDomainShared(FileDomain):
    def delete_user_dir(self):
        pass

    @property
    def name(self):
        return 'shared'

    @property
    def user_dir(self):
        return os.path.join(self._mount_dir, 'shared')

class HostpathVolumeMixin(object):
    def create_volume(self):
        # Create persistent volume and claim.
        kubernetes_client = KubernetesClient()
        volume_names = [pvc.metadata.name for pvc in kubernetes_client.list_persistent_volume_claims(namespace=self._user.namespace)]
        if self.volume_name in volume_names:
            return

        template = Template(HOSTPATH_VOLUME_TEMPLATE)
        template.NAME = self.volume_name
        template.PATH = urlparse(self.url).path
        kubernetes_client.apply_yaml_data(template.yaml.encode(), namespace=self._user.namespace)

    def delete_volume(self):
        kubernetes_client = KubernetesClient()

        # Delete anyway, as the namespace may already be deleted.
        template = Template(HOSTPATH_VOLUME_TEMPLATE)
        template.NAME = self.volume_name
        template.PATH = urlparse(self.url).path
        kubernetes_client.delete_yaml_data(template.yaml.encode(), namespace=self._user.namespace)

class PrivateFileDomain(FileDomainPrivate, HostpathVolumeMixin):
    @property
    def url(self):
        return 'file://%s' % os.path.join(self._url.path, 'private', self._user.username)

class SharedFileDomain(FileDomainShared, HostpathVolumeMixin):
    @property
    def url(self):
        return 'file://%s' % os.path.join(self._url.path, 'shared')
