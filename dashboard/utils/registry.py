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
from dxf import DXF
from base64 import b64encode


class RegistryClient(object):
    def __init__(self, registry_url, registry_cert_file):
        self._registry_url = urlparse(registry_url)
        self._registry_host = '%s:%s' % (self._registry_url.hostname, self._registry_url.port)
        self._registry_cert_file = registry_cert_file

    @property
    def safe_registry_url(self):
        return '%s://%s' % (self._registry_url.scheme, self._registry_host)

    @property
    def registry_host(self):
        return self._registry_host

    def _auth(self, dxf, response):
        if self._registry_url.username and self._registry_url.password:
            if self._registry_url.scheme == 'http':
                # DXF will not authenticate over HTTP
                dxf._headers = {'Authorization': 'Basic ' + b64encode(('%s:%s' % (self._registry_url.username, self._registry_url.password)).encode('utf-8')).decode('utf-8')}
                return
            dxf.authenticate(self._registry_url.username, self._registry_url.password, response=response)

    def registry(self, repository=''):
        return DXF(self._registry_host, repository, auth=self._auth, insecure=self._registry_url.scheme == 'http', tlsverify=self._registry_cert_file if self._registry_cert_file else True)

    def add_image(self, filename, name, tag):
        # Check for image with same name and tag.
        for repository in self.registry().list_repos():
            registry = self.registry(repository)
            for alias in registry.list_aliases():
                if name == repository and tag == alias:
                    raise ValueError('Image with same name and tag already exists')

        command = ''
        if self._registry_cert_file:
            command += 'export SSL_CERT_FILE=%s; ' % self._registry_cert_file
        if self._registry_url.username and self._registry_url.password:
            command += 'crane auth login -u \'%s\' -p \'%s\' %s; ' % (self._registry_url.username,
                                                                      self._registry_url.password,
                                                                      self.registry_host)
        command += 'crane push %s %s/%s:%s' % (filename, self.registry_host, name, tag)
        if os.system(command) != 0:
            raise SystemError('Can not push image to registry')
