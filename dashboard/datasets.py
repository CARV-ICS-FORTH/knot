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

from .services import ServiceTemplateManager, ServiceManager
from .utils.kubernetes import KubernetesClient
from .utils.helm import HelmLocalRepoClient, HelmClient


class DatasetTemplateManager(ServiceTemplateManager):
    def __init__(self, user):
        self.user = user
        self.repos = {'system': HelmLocalRepoClient('system', settings.DATASETS_REPO_DIR)}

    def list(self):
        charts = {name: dict(chart, repo='system') for name, chart in self.repos['system'].list().items() if name not in settings.DISABLED_SERVICES}

        valid_keys = ('name', 'description', 'version', 'repo', 'private')
        return [{k: v for k, v in chart.items() if k in valid_keys} for name, chart in charts.items()]

class DatasetManager(ServiceManager):
    def list(self):
        kubernetes_client = KubernetesClient()
        helm_client = HelmClient(kubernetes_client)
        releases = helm_client.list(self.user.namespace)

        contents = []
        for dataset in kubernetes_client.list_crds(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self.user.namespace, plural='datasets'):
            # Keep only datasets that are part of releases.
            try:
                release_name = dataset['metadata']['annotations']['meta.helm.sh/release-name']
            except:
                continue
            release = next((release for release in releases if release['name'] == release_name), None)
            if not release:
                continue

            # Filter out datasets that are marked as hidden.
            try:
                if 'knot-hidden' in dataset['metadata']['labels'].keys():
                    continue
            except:
                pass

            try:
                dataset_type = dataset['spec']['local']['type']
                if dataset_type in ('COS', 'H3', 'ARCHIVE'):
                    contents.append({'name': dataset['metadata']['name'], **dataset['spec']['local']})
            except:
                continue

        return contents
