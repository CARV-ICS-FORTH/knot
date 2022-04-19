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
        self._harbor_oidc_url = '%s://%s/c/oidc/login' % (self._harbor_url.scheme, self._harbor_host)

    @property
    def registry_host(self):
        return self._harbor_host

    def _request(self, method, url, **kwargs):
        kwargs.setdefault('verify', False if os.environ.get('VIRTUAL_ENV') else True) # XXX Do not verify if running in virtual environment.
        kwargs.setdefault('timeout', 30)
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _head(self, path, params={}):
        kwargs.setdefault('allow_redirects', False)
        self._request('head', '%s/%s' % (self._harbor_api_url, path.lstrip('/')), auth=self._harbor_api_auth, params=params)

    def _get(self, path, params={}):
        response = self._request('get', '%s/%s' % (self._harbor_api_url, path.lstrip('/')), auth=self._harbor_api_auth, params=params)
        return response.json()

    def _put(self, path, data={}):
        self._request('put', '%s/%s' % (self._harbor_api_url, path.lstrip('/')), auth=self._harbor_api_auth, json=data)

    def _post(self, path, data={}):
        self._request('post', '%s/%s' % (self._harbor_api_url, path.lstrip('/')), auth=self._harbor_api_auth, json=data)

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

    def add_user_to_project(self, user, project_name, role_id, public=False):
        # Create project if it does not exist.
        try:
            result = self._head('/projects', params={'project_name': project_name})
        except:
            try:
                self._post('/projects', data={'project_name': project_name,
                                              'public': public})
            except:
                # print('Cannot create Harbor project "%s".' % project_name)
                return None

        # Add user to project.
        try:
            result = self._get('/projects/%s/members' % project_name)
            member = next((item for item in result if item['entity_name'] == user.username), None)
        except:
            # print('Cannot get members of Harbor project "%s".' % project_name)
            return None

        # Assume we are ok if the username is found.
        if member:
            return True

        try:
            self._post('/projects/%s/members' % project_name, data={'project_name_or_id': project_name,
                                                                    'member_user': {'username': user.username},
                                                                    'role_id': role_id})
        except:
            # print('Cannot add member "%s" to Harbor project "%s".' % (user.username, project_name))
            return None

        return True

    def create_user_id(self, user):
        # First, get a cookie and OIDC request URL from Harbor.
        response = self._request('get', self._harbor_oidc_url, allow_redirects=False)
        response.raise_for_status()
        harbor_sid = response.cookies.get('sid')
        grant_request_url = response.headers['Location']

        # Second, generate a grant internally and get the login request URL.
        from oauth2_provider.models import Application
        from oauth2_provider.oauth2_validators import OAuth2Validator
        from oauthlib.common import Request
        from oauthlib.oauth2 import AuthorizationCodeGrant, BearerToken

        request = Request(grant_request_url)
        request.user = user # XXX We need the user model because of this.
        validator = OAuth2Validator()
        token = BearerToken(validator)
        grant = AuthorizationCodeGrant(validator)
        login_request_url = grant.create_authorization_response(request, token)[0]['Location']

        # Third, login to Harbor with the code from the grant.
        response = self._request('get', login_request_url, cookies={'sid': harbor_sid}, allow_redirects=False)
        response.raise_for_status()

    def get_user_id(self, username):
        try:
            result = self._get('/users/search', params={'username': username})
            return next((item['user_id'] for item in result if item['username'] == username), None)
        except:
            # print('Cannot retrieve id for user "%s".' % username)
            return SystemError

    def get_cli_url(self, user):
        try:
            user_id = self.get_user_id(user.username)
        except:
            return None

        # Try to create user if not found.
        if user_id is None:
            try:
                # print('Adding user "%s" to Harbor.' % user.username)
                self.create_user_id(user)
                user_id = self.get_user_id(user.username)
            except:
                return None

        if user_id is None:
            return None

        try:
            cli_secret = self._get('/users/%s' % user_id)['oidc_user_meta']['secret']
        except:
            # print('Cannot retrieve Harbor CLI secret for user "%s".' % username)
            return None

        return '%s://%s:%s@%s' % (self._harbor_url.scheme, user.username, cli_secret, self._harbor_host)
