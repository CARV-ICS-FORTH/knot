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

from django.conf import settings as django_settings

def settings(request):
    return {'version': django_settings.VERSION,
            'dashboard_title': django_settings.DASHBOARD_TITLE,
            'documentation_url': django_settings.DOCUMENTATION_URL,
            'issues_url': django_settings.ISSUES_URL,
            'images_available': True if django_settings.REGISTRY_URL else False,
            'datasets_available': django_settings.DATASETS_AVAILABLE,
            'jupyterhub_url': django_settings.JUPYTERHUB_URL,
            'argo_workflows_url': django_settings.ARGO_WORKFLOWS_URL}
