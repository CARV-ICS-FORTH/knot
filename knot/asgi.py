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

"""
ASGI config for knot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

import dashboard.routing

from collections import namedtuple
from channels.db import database_sync_to_async
from channels.auth import AuthMiddlewareStack, UserLazyObject
from channels.middleware import BaseMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knot.settings')

@database_sync_to_async
def get_impersonated_user(scope):
    from impersonate.middleware import ImpersonateMiddleware

    request = namedtuple('Request', 'user session path')
    request.user = scope['user']
    request.session = scope['session']
    request.path = scope['path']

    impersonate_middleware = ImpersonateMiddleware()
    impersonate_middleware.process_request(request)
    if request.impersonator:
        return request.user

class AsyncImpersonateMiddleware(BaseMiddleware):
    '''
    Middleware which populates scope['user'] in case of impersonation.
    '''

    def populate_scope(self, scope):
        if 'user' not in scope:
            raise ValueError(
                'Cannot find user in scope. You should wrap your consumer in AuthMiddleware.'
            )

    async def resolve_scope(self, scope):
        impersonated_user = await get_impersonated_user(scope)
        if impersonated_user:
            scope['user'] = impersonated_user

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        self.populate_scope(scope)
        await self.resolve_scope(scope)
        return await super().__call__(scope, receive, send)

application = ProtocolTypeRouter({'http': get_asgi_application(),
                                  'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(AsyncImpersonateMiddleware(URLRouter(dashboard.routing.websocket_urlpatterns))))})
