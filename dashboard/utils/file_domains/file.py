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

from urllib.parse import urlparse
from datetime import datetime


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

    def exists(self, name=None):
        return os.path.exists(self.real_path if not name else os.path.join(self.real_path, name))

    def isfile(self, name=None):
        return os.path.isfile(self.real_path if not name else os.path.join(self.real_path, name))

    def isdir(self, name=None):
        return os.path.isdir(self.real_path if not name else os.path.join(self.real_path, name))

    def open(self, name, mode):
        return open(os.path.join(self.real_path, name), mode)

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
        os.mkdir(os.path.join(self.real_path, name))

    def rmdir(self, name):
        os.rmdir(os.path.join(self.real_path, name))

    def upload(self, files):
        for f in files:
            with open(os.path.join(self.real_path, f.name), 'wb') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

    def download(self, name, response):
        zip_path = os.path.join(self.real_path, name)
        with zipfile.ZipFile(response, 'w') as zip_file:
            for root, dirs, files in os.walk(zip_path):
                for file in files:
                    zip_add_file = os.path.join(root, file)
                    zip_file.write(zip_add_file, zip_add_file[len(os.path.dirname(zip_path)):])

    def remove(self, name):
        os.remove(os.path.join(self.real_path, name))

class FileDomain(object):
    def __init__(self, url, mount_dir, user):
        if not user:
            raise ValueError('Empty user')

        self._url = urlparse(url)
        if self._url.scheme != 'file':
            raise ValueError('Unsupported file domain URL')
        self._mount_dir = mount_dir
        self._user = user
        self.create_user_dir()

    def create_user_dir(self):
        if not os.path.exists(self.user_dir):
            os.makedirs(self.user_dir)

    @property
    def name(self):
        ''' How to name the domain when mounting it ("private" or "shared"). '''
        raise NotImplementedError

    @property
    def volume_name(self):
        ''' How to name the volume when mounting it. '''
        return 'karvdash-volume-%s' % self.name

    @property
    def mount_dir(self):
        ''' Where to mount the domain. '''
        raise NotImplementedError

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

class PrivateFileDomain(FileDomain):
    @property
    def name(self):
        return 'private'

    @property
    def mount_dir(self):
        return os.path.join(self._mount_dir, 'private')

    @property
    def user_dir(self):
        return os.path.join(self._mount_dir, 'private', self._user.username)

    @property
    def url(self):
        return 'file://%s' % os.path.join(self._url.path, 'private', self._user.username)

class SharedFileDomain(FileDomain):
    @property
    def name(self):
        return 'shared'

    @property
    def mount_dir(self):
        return os.path.join(self._mount_dir, 'shared')

    @property
    def user_dir(self):
        return os.path.join(self._mount_dir, 'shared')

    @property
    def url(self):
        return 'file://%s' % os.path.join(self._url.path, 'shared')
