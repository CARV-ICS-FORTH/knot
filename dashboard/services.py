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
import string
import tempfile

from django.conf import settings
from urllib.parse import urlparse
from ruamel.yaml import YAML

from .utils.kubernetes import KubernetesClient
from .utils.helm import flatten_values, unflatten_values, HelmLocalRepoClient, HelmRemoteRepoClient, HelmClient


class ServiceTemplateManager(object):
    def __init__(self, user):
        self.user = user
        self.repos = {'local': HelmLocalRepoClient('local', settings.SERVICES_REPO_DIR),
                      'shared': None,
                      'private': None}
        del(self.repos['local']) # Comment out to work on local charts.
        if self.repo_base_url:
            self.repos['shared'] = HelmRemoteRepoClient('library', '%s/%s' % (self.repo_base_url, 'library'), repo_password=settings.HARBOR_ADMIN_PASSWORD)
            if self.user.username != 'admin':
                self.repos['private'] = HelmRemoteRepoClient(self.user.namespace, '%s/%s' % (self.repo_base_url, self.user.username), repo_password=settings.HARBOR_ADMIN_PASSWORD)

    @property
    def repo_base_url(self):
        return '%s/chartrepo' % settings.HARBOR_URL.rstrip('/') if settings.HARBOR_URL else None

    def get_template(self, name):
        return next((chart for chart in self.list() if chart['name'] == name), None)

    def list(self):
        charts = {}
        for repo_name, repo in self.repos.items():
            if not repo:
                continue
            repo_charts = {name: dict(chart, repo=repo_name, private=(repo_name == 'private')) for name, chart in repo.list().items()}
            if repo_name == 'local':
                repo_charts = {name: chart for name, chart in repo_charts.items() if name not in settings.DISABLED_SERVICES}
            charts.update(repo_charts)

        valid_keys = ('name', 'description', 'version', 'repo', 'private')
        return [{k: v for k, v in chart.items() if k in valid_keys} for name, chart in charts.items()]

    def variables(self, name):
        try:
            template = self.get_template(name)
        except:
            template = None
        if not template:
            raise KeyError

        repo_client = self.repos[template['repo']]
        chart_name, values = repo_client.values(name)
        data = flatten_values(values, 'data')

        data.insert(0, {'label': 'name',
                        'default': name,
                        'type': 'str'})
        return chart_name, data

class ServiceManager(object):
    def __init__(self, user):
        self.user = user

    def list(self):
        kubernetes_client = KubernetesClient()
        helm_client = HelmClient(kubernetes_client)
        releases = helm_client.list(self.user.namespace)

        ingress_url = urlparse(settings.INGRESS_URL)

        contents = []
        ingresses = kubernetes_client.list_ingresses(namespace=self.user.namespace)
        for service in kubernetes_client.list_services(namespace=self.user.namespace):
            # Keep only services that are part of releases.
            try:
                release_name = service.metadata.annotations['meta.helm.sh/release-name']
            except:
                continue
            release = next((release for release in releases if release['name'] == release_name), None)
            if not release:
                continue

            # Filter out services that are marked as hidden.
            try:
                if 'knot-hidden' in service.metadata.labels.keys():
                    continue
            except:
                pass

            # Get URL from associated ingress.
            name = service.metadata.name
            url = None
            for ingress in ingresses:
                try:
                    release_name = service.metadata.annotations['meta.helm.sh/release-name']
                except:
                    continue
                if release_name != release['name']:
                    continue
                try:
                    for rule in ingress.spec.rules:
                        for path in rule.http.paths:
                            if path.backend.service.name == name and rule.host:
                                url = '%s://%s%s' % (ingress_url.scheme, rule.host, path.path if (path.path and path.path != '/') else '')
                                break
                        if url:
                            break
                except:
                    pass
                if url:
                    break

            contents.append({'name': name,
                             'url': url,
                             'created': service.metadata.creation_timestamp,
                             'release': release})

        return contents

    def variables(self, name):
        kubernetes_client = KubernetesClient()
        helm_client = HelmClient(kubernetes_client)
        try:
            release = next((r for r in helm_client.list(self.user.namespace) if r['name'] == name), None)
        except:
            release = None
        if not release:
            raise KeyError

        values = helm_client.values(self.user.namespace, name)
        data = flatten_values(values, 'data')

        data.insert(0, {'label': 'name',
                        'default': name,
                        'type': 'str'})
        return data

    def create(self, chart_name, variables, data, set_local_data=True):
        variables = [variable for variable in variables if not variable['label'].startswith('data.knot.')]
        for variable in variables:
            value = data.get(variable['label'])
            if value is None:
                continue
            variable['value'] = value

        kubernetes_client = KubernetesClient()
        helm_client = HelmClient(kubernetes_client)

        # Resolve naming conflicts.
        name = data['name']
        names = [release['name'] for release in helm_client.list(self.user.namespace)]
        while name in names:
            name = data['name'] + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])

        if set_local_data:
            # Generate service URLs.
            if settings.GENERATE_SERVICE_URLS:
                prefix = '%s-%s' % (name, self.user.username)
            else:
                # XXX Non-atomic prefix selection.
                used_prefixes = []
                for ingress in kubernetes_client.list_ingresses(namespace=''):
                    try:
                        used_prefixes.append(ingress.spec.rules[0].host.split('.', 1)[0])
                    except:
                        pass
                available_prefixes = list(set(settings.SERVICE_URL_PREFIXES) - set(used_prefixes))
                if not available_prefixes:
                    raise SystemError('There are no more available service URLs.')
                prefix = random.choice(available_prefixes)

            ingress_url = urlparse(settings.INGRESS_URL)
            ingress_host = '%s:%s' % (ingress_url.hostname, ingress_url.port) if ingress_url.port else ingress_url.hostname

            # Set hostname, registry and storage paths, and other local variables.
            variables += [{'label': 'data.knot.enabled',
                           'value': True},
                          {'label': 'data.knot.hostname',
                           'value': '%s.%s' % (prefix, ingress_host)}]
            for key, value in self.user.local_data.items():
                key = ''.join((word.title() if i > 0 else word) for i, word in enumerate(key.split('_'))) # Convert to lowerCamelCase.
                variables.append({'label': 'data.knot.' + key, 'value': value})

        # Apply.
        self.user.update_kubernetes_credentials(kubernetes_client=kubernetes_client)
        with tempfile.NamedTemporaryFile() as f:
            YAML().dump(unflatten_values(variables)['data'], f)
            helm_client.install(self.user.namespace, name, chart_name, f.name)

        return name

    def delete(self, name):
        helm_client = HelmClient()
        helm_client.uninstall(self.user.namespace, name)
