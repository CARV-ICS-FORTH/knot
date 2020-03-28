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

from configparser import ConfigParser


class API:
    def __init__(self, config_path=None):
        self.config_path = config_path if config_path else self._get_config_path()
        self.base_url, self.token = self._get_configuration(self.config_path)

    def _get_config_path(self):
        try:
            return os.environ['KARVDASH_CONFIG']
        except KeyError:
            config_path = os.path.join(os.getcwd(), 'config.ini')
            if not os.access(config_path, os.F_OK):
                config_path = os.path.join(os.environ['HOME'], '.karvdash', 'config.ini')

            return config_path

    def _get_configuration(self, config_path):
        config = ConfigParser()
        config.read(config_path)
        if 'Karvdash' not in config:
            raise ValueError('Missing "Karvdash" section in API client configuration file')
        karvdash_config = config['Karvdash']
        if 'base_url' not in karvdash_config:
            raise ValueError('Missing "base_url" value in Karvdash API client configuration file')
        base_url = config['Karvdash']['base_url'].rstrip('/')
        if 'token' not in karvdash_config:
            raise ValueError('Missing "token" value in Karvdash API client configuration file')
        token = config['Karvdash']['token'].strip()
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

    def delete_service(self, name):
        r = requests.delete(self.base_url + '/services/%s/' % name, headers=self._headers)
        return r.status_code == requests.codes.no_content

    def list_templates(self):
        r = requests.get(self.base_url + '/templates/', headers=self._headers)
        return r.json()

    def inject(self, data):
        r = requests.post(self.base_url + '/utils/inject/', data=data, headers=self._headers)
        return r.text
