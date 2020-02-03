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

import docker

from urllib.parse import urlparse
from dxf import DXF


class DockerClient(object):
    def __init__(self, registry_url):
        self._registry_url = urlparse(registry_url)
        self._registry_host = '%s:%s' % (self._registry_url.hostname, self._registry_url.port)
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = docker.from_env()
        return self._client

    @property
    def registry_host(self):
        return self._registry_host

    def registry(self, repository=''):
        return DXF(self._registry_host, repository, insecure=self._registry_url.scheme == 'http')

    def add_image(self, data, name, tag='latest'):
        images = self.client.images.load(data)
        if len(images) == 0:
            raise ValueError('No images present in file')
        if len(images) != 1:
            raise ValueError('More than one images present in file')
        image = images[0]
        repository = '%s/%s' % (self._registry_host, name)
        if not image.tag(repository, tag=tag):
            raise ValueError('Can not tag image')
        self.client.images.push(repository, tag=tag, stream=False)
