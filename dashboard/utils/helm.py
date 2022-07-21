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
import subprocess
import requests
import shlex

from requests.auth import HTTPBasicAuth
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from packaging import version
from datetime import datetime

from .kubernetes import KubernetesClient


def flatten_values(values, prefix=''):
    data = []
    for key, value in values.items():
        label = '%s.%s' % (prefix, key) if prefix else key
        comment = values.ca.get(key, 2)
        if type(values[key]) == CommentedMap:
            data += flatten_values(values[key], label)
        else:
            data.append({'label': label,
                         'default': value,
                         'type': 'int' if type(value) == int else 'str',
                         'help': comment.value.lstrip('#').strip() if comment else ''})
    return data

def unflatten_values(data):
    values = {}
    for item in data:
        value_dict = values
        key = item['label']
        while '.' in key:
            prefix, key = key.split('.', 1)
            if prefix not in value_dict.keys():
                value_dict[prefix] = {}
            value_dict = value_dict[prefix]
        value_dict[key] = int(item['value']) if ('type' in item.keys() and item['type'] == 'int') else item['value']
    return values

class HelmLocalRepoClient(object):
    def __init__(self, repo_name, repo_path):
        self._repo_name = repo_name
        self._repo_path = repo_path

    def _load_yaml(self, yaml_path):
        if not os.path.isfile(yaml_path):
            return None
        try:
            with open(yaml_path, 'rb') as f:
                return YAML().load(f)
        except:
            return None

    def list(self, latest_only=True):
        result = {}
        for chart_path in [os.path.join(d.path, 'Chart.yaml') for d in os.scandir(self._repo_path) if d.is_dir()]:
            chart_info = self._load_yaml(chart_path)
            if not chart_info:
                continue
            result[chart_info['name']] = chart_info

        return result

    def values(self, name):
        chart_name = os.path.join(self._repo_path, name)
        return chart_name, self._load_yaml(os.path.join(chart_name, 'values.yaml'))

class HelmRemoteRepoClient(object):
    def __init__(self, repo_name, repo_url, repo_username='admin', repo_password=''):
        self._repo_name = repo_name
        self._repo_url = repo_url
        self._repo_auth = HTTPBasicAuth(repo_username, repo_password) if repo_password else None

    def _request(self, method, url, **kwargs):
        kwargs.setdefault('verify', False if os.environ.get('VIRTUAL_ENV') else True) # XXX Do not verify if running in virtual environment.
        kwargs.setdefault('timeout', 30)
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _get(self, path, params={}):
        response = self._request('get', '%s/%s' % (self._repo_url, path.lstrip('/')), auth=self._repo_auth, params=params)
        return YAML(typ='safe').load(response.text)

    def _local_repo_list(self):
        command = 'helm repo list -o yaml'
        try:
            result = subprocess.check_output(command, shell=True)
            return YAML(typ='safe').load(result)
        except:
            return []

    def _local_repo_add(self):
        command = 'helm repo add %s --username=%s --password=%s %s %s' % ('--insecure-skip-tls-verify' if os.environ.get('VIRTUAL_ENV') else '', # XXX Do not verify if running in virtual environment.
                                                                          self._repo_auth.username,
                                                                          shlex.quote(self._repo_auth.password),
                                                                          self._repo_name,
                                                                          self._repo_url)
        subprocess.check_output(command, shell=True)

    def _local_repo_update(self):
        command = 'helm repo update %s' % self._repo_name
        subprocess.check_output(command, shell=True)

    def list(self, latest_only=True):
        result = self._get('index.yaml')
        if not latest_only:
            return result['entries']
        return {name: max(versions, key=lambda x: version.parse(x['version'])) for name, versions in result['entries'].items()}

    def values(self, name):
        if not next((repo for repo in self._local_repo_list() if repo['name'] == self._repo_name), None):
            self._local_repo_add()
        self._local_repo_update()

        chart_name = '%s/%s' % (self._repo_name, name)
        command = 'helm show values %s %s' % ('--insecure-skip-tls-verify' if os.environ.get('VIRTUAL_ENV') else '', # XXX Do not verify if running in virtual environment.
                                              chart_name)
        result = subprocess.check_output(command, shell=True)
        return chart_name, YAML().load(result)

class HelmClient(object):
    def __init__(self, kubernetes_client=None):
        self.kubernetes_client = kubernetes_client if kubernetes_client else KubernetesClient()

    def list(self, namespace):
        secrets = self.kubernetes_client.list_secrets(namespace)
        releases = [secret.metadata.labels for secret in secrets if secret.type.startswith('helm.sh/release')]

        for release in releases:
            release['modified'] = datetime.fromtimestamp(int(release['modifiedAt']))
        valid_keys = ('name', 'status', 'modified', 'version')
        return [{k: v for k, v in release.items() if k in valid_keys} for release in releases]

    def values(self, namespace, name):
        command = 'helm get values -o yaml -n %s %s' % (namespace, name)
        result = subprocess.check_output(command, shell=True)
        return YAML().load(result)

    def install(self, namespace, name, chart_name, values_file):
        command = 'helm install %s -n %s -f %s %s %s' % ('--insecure-skip-tls-verify' if os.environ.get('VIRTUAL_ENV') else '', # XXX Do not verify if running in virtual environment.
                                                         namespace,
                                                         values_file,
                                                         name,
                                                         chart_name)
        subprocess.check_output(command, shell=True)

    def uninstall(self, namespace, name):
        command = 'helm uninstall -n %s %s' % (namespace, name)
        subprocess.check_output(command, shell=True)
