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

import subprocess

from celery import shared_task

from .models import User
from .services import ServiceTemplateManager, ServiceManager


@shared_task
def create_service_task(user_id, service_name, variables, data, upgrade=False):
    user = User.objects.get(pk=user_id)

    # Adds the Helm repository locally.
    template_manager = ServiceTemplateManager(user)
    try:
        chart_name, _ = template_manager.variables(service_name)
    except Exception as e:
        user.send_update('create_service')
        raise ValueError('Can not %s service: %s' % ('upgrade' if upgrade else 'create', str(e)))

    service_manager = ServiceManager(user)
    try:
        service_name = service_manager.create(chart_name, variables, data, upgrade=upgrade)
    except subprocess.CalledProcessError as e:
        user.send_update('create_service')
        raise ValueError('Can not %s service: %s' % ('upgrade' if upgrade else 'create', str(e)))
    except Exception as e:
        user.send_update('create_service')
        raise ValueError('Can not %s service: %s' % ('upgrade' if upgrade else 'create', str(e)))

    user.send_update('create_service')
    return 'Service "%s" %s.' % (service_name, 'upgraded' if upgrade else 'created')
