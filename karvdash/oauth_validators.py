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

from django.conf import settings
from urllib.parse import urlparse
from oauth2_provider.oauth2_validators import OAuth2Validator


class CustomOAuth2Validator(OAuth2Validator):
    def get_additional_claims(self, request):
        registry_url = urlparse(settings.REGISTRY_URL)
        return {
            'sub': request.user.username,
            'preferred_username': request.user.username,
            'email': request.user.email,
            'name': request.user.get_full_name(),
            'given_name': request.user.first_name,
            'family_name': request.user.last_name,
            'karvdash_namespace': 'karvdash-%s' % request.user.username,
            'karvdash_ingress_url': settings.INGRESS_URL,
            'karvdash_registry_url': '%s://%s:%s' % (registry_url.scheme, registry_url.hostname, registry_url.port),
            'karvdash_argo_workflows_url': settings.ARGO_WORKFLOWS_URL
        }
