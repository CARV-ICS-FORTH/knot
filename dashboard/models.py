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

import random

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


def generate_token():
    return ''.join(random.choice('0123456789abcdef') for n in range(40))

class APIToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    token = models.CharField(max_length=64, blank=False, null=False, default=generate_token())

@receiver(user_logged_in)
def create_api_token(sender, user, request, **kwargs):
    try:
        api_token = APIToken.objects.get(user=user)
    except APIToken.DoesNotExist:
        api_token = APIToken(user=user)
        api_token.save()
