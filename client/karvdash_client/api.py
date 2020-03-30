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
import requests

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser


class API:
    def __init__(self, config_path=None):
        self.config_path = config_path if config_path else self._get_config_path()
        self.base_url, self.token = self._get_configuration(self.config_path)

    def _get_config_path(self):
        try:
            return os.environ['KARVDASH_CONFIG']
        except KeyError:
            pass

        config_paths = [os.path.join(os.environ['HOME'], '.karvdash', 'config.ini'),
                        '/var/lib/karvdash/config.ini']
        for config_path in config_paths:
            if os.access(config_path, os.F_OK):
                return config_path

        return config_paths[0]

    def _get_configuration(self, config_path):
        config = ConfigParser()
        config.read(config_path)
        base_url = config.get('Karvdash', 'base_url').rstrip('/')
        token = config.get('Karvdash', 'token').strip()
        return base_url, token

    @property
    def _headers(self):
        return {'Authorization': 'Token %s' % self.token.lower()}

    def list_services(self):
        r = requests.get(self.base_url + '/services/', headers=self._headers)
        return r.json()

    def create_service(self, filename, variables):
        data = {k.upper(): v for k, v in variables.items()}
        data['filename'] = filename
        r = requests.post(self.base_url + '/services/', json=data, headers=self._headers)
        return r.json()

    def exec_service(self, name, command):
        data = {'command': command}
        r = requests.post(self.base_url + '/services/%s/' % name, json=data, headers=self._headers)
        return r.json()

    def delete_service(self, name):
        r = requests.delete(self.base_url + '/services/%s/' % name, headers=self._headers)
        return r.status_code == requests.codes.no_content

    def list_templates(self):
        r = requests.get(self.base_url + '/templates/', headers=self._headers)
        return r.json()

    def inject(self, data):
        r = requests.post(self.base_url + '/utils/inject/', data=data, headers=self._headers)
        return r.text
