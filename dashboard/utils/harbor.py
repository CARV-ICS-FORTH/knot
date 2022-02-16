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

from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth


class HarborClient(object):
    ROLE_ADMIN = 1
    ROLE_DEVELOPER = 2
    ROLE_GUEST = 3
    ROLE_MAINTAINER = 4

    def __init__(self, harbor_url, harbor_admin_password=''):
        self._harbor_url = urlparse(harbor_url)
        self._harbor_host = '%s:%s' % (self._harbor_url.hostname, self._harbor_url.port) if self._harbor_url.port else self._harbor_url.hostname
        self._harbor_api_url = '%s://%s/api/v2.0' % (self._harbor_url.scheme, self._harbor_host)
        self._harbor_api_auth = HTTPBasicAuth('admin', harbor_admin_password)

    @property
    def registry_host(self):
        return self._harbor_host

    def _head(self, path, params={}):
        response = requests.head('%s/%s' % (self._harbor_api_url, path.lstrip('/')),
                                 auth=self._harbor_api_auth,
                                 verify=False if os.environ.get('VIRTUAL_ENV') else True, # XXX Do not verify if running in virtual environment.
                                 timeout=30,
                                 params=params)
        response.raise_for_status()
        return

    def _get(self, path, params={}):
        return requests.get('%s/%s' % (self._harbor_api_url, path.lstrip('/')),
                            auth=self._harbor_api_auth,
                            verify=False if os.environ.get('VIRTUAL_ENV') else True, # XXX Do not verify if running in virtual environment.
                            timeout=30,
                            params=params).json()

    def _put(self, path, data={}):
        response = requests.put('%s/%s' % (self._harbor_api_url, path.lstrip('/')),
                                auth=self._harbor_api_auth,
                                verify=False if os.environ.get('VIRTUAL_ENV') else True, # XXX Do not verify if running in virtual environment.
                                timeout=30,
                                json=data)
        response.raise_for_status()
        return

    def _post(self, path, data={}):
        response = requests.post('%s/%s' % (self._harbor_api_url, path.lstrip('/')),
                                 auth=self._harbor_api_auth,
                                 verify=False if os.environ.get('VIRTUAL_ENV') else True, # XXX Do not verify if running in virtual environment.
                                 timeout=30,
                                 json=data)
        response.raise_for_status()
        return

    def configure(self, oidc_client_id, oidc_client_secret, oidc_endpoint):
        try:
            self._put('configurations', data={'auth_mode': 'oidc_auth',
                                              'oidc_auto_onboard': True,
                                              'oidc_client_id': oidc_client_id,
                                              'oidc_client_secret': oidc_client_secret,
                                              'oidc_endpoint': oidc_endpoint,
                                              'oidc_name': 'karvdash',
                                              'oidc_scope': 'openid,profile,email',
                                              'oidc_user_claim': 'sub',
                                              'project_creation_restriction': 'adminonly'})
        except:
            return False

        return True

    def add_user_to_project(self, project_name, username, role_id, public=False):
        # Create project if it does not exist.
        try:
            result = self._head('/projects', params={'project_name': project_name})
        except:
            try:
                self._post('/projects', data={'project_name': project_name,
                                              'public': public})
            except:
                print('Cannot create Harbor project "%s".' % project_name)
                return None

        # Add user to project.
        try:
            result = self._get('/projects/%s/members' % project_name)
            member = next((item for item in result if item['entity_name'] == username), None)
        except:
            print('Cannot get members of Harbor project "%s".' % project_name)
            return None

        # Assume we are ok if the username is found.
        if member:
            return True

        try:
            self._post('/projects/%s/members' % project_name, data={'project_name_or_id': project_name,
                                                                    'member_user': {'username': username},
                                                                    'role_id': role_id})
        except:
            print('Cannot add member "%s" to Harbor project "%s".' % (username, project_name))
            return None

        return True

    def get_cli_url(self, username):
        cli_secret = ''
        try:
            result = self._get('/users/search', params={'username': username})
            user_id = next((item['user_id'] for item in result if item['username'] == username), None)
            if user_id:
                cli_secret = self._get('/users/%s' % user_id)['oidc_user_meta']['secret']
        except TypeError:
            print('Cannot retrieve Harbor CLI secret for user %s. Probably wrong admin password.' % username)
            return None
        except:
            print('Cannot retrieve Harbor CLI secret for user %s. Probably Harbor is down.' % username)
            return None

        if not user_id:
            return None

        return '%s://%s:%s@%s' % (self._harbor_url.scheme, username, cli_secret, self._harbor_host)
