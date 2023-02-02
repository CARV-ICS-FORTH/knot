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

from .models import User


def custom_allow(request):
    '''
    Return whether the user is allowed to impersonate.
    '''

    if request.user.is_staff:
        return True
    if request.user.memberships.exists():
        return True
    return False


def custom_user_queryset(request):
    '''
    Return a queryset containing the users a user can impersonate.
    '''

    if request.user.is_staff:
        return User.objects.all()
    return User.objects.filter(members__user=request.user)
