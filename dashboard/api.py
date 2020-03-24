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

from django.conf import settings
from restless.dj import DjangoResource

from .utils.kubernetes import KubernetesClient


def namespace_for_user(user):
    return 'karvdash-%s' % user.username

class ServiceResource(DjangoResource):
    http_methods = {'list': {'GET': 'list'},
                    'detail': {'DELETE': 'delete'}}

    def list(self):
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.request.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        # Get service names from our database.
        service_database = []
        for file_name in os.listdir(service_database_path):
            if file_name.endswith('.yaml'):
                service_database.append(file_name[:-5])

        # Fill in the contents.
        contents = []
        for service in kubernetes_client.list_services(namespace=namespace_for_user(self.request.user), label_selector=''):
            name = service.metadata.name
            # ports = [str(p.port) for p in service.spec.ports if p.protocol == 'TCP']
            contents.append({'name': name,
                             'url': 'http://%s-%s.%s' % (name, self.request.user.username, settings.INGRESS_DOMAIN),
                             'created': service.metadata.creation_timestamp,
                             'actions': True if name in service_database else False})

        return contents

    def delete(self, pk):
        print('*** Deleting %s' % pk)
