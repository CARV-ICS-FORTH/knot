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

import json

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync


class UpdatesConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            self.close()

        self.group_name = 'updates_%s' % self.user.username

        # Join group of user-specific updates.
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        # Leave group of user-specific updates.
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    # Receive message for group.
    def update_message(self, event):
        message = event['message']

        # Send message over WebSocket.
        self.send(text_data=json.dumps({'message': message}))
