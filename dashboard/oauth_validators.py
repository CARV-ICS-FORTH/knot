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

from oauth2_provider.oauth2_validators import OAuth2Validator

from .models import User


class CustomOAuth2Validator(OAuth2Validator):
    def get_additional_claims(self, request):
        user = User.objects.get(pk=request.user.pk)

        claims = {'sub': user.username,
                  'preferred_username': user.username,
                  'email': user.email if user.email else user.username, # Teams lack email.
                  'name': user.get_full_name(),
                  'given_name': user.first_name,
                  'family_name': user.last_name}
        claims.update({('knot_%s' % key): value for key, value in user.local_data.items()})
        return claims
