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

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

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
        if not os.path.isdir(self._repo_path):
            return result
        for chart_path in [os.path.join(d.path, 'Chart.yaml') for d in os.scandir(self._repo_path) if d.is_dir()]:
            chart_info = self._load_yaml(chart_path)
            if not chart_info:
                continue
            result[chart_info['name']] = chart_info

        return result

    def values(self, name):
        chart_name = os.path.join(self._repo_path, name)
        return chart_name, self._load_yaml(os.path.join(chart_name, 'values.yaml'))

class HelmClient(object):
    def __init__(self, kubernetes_client=None):
        self.kubernetes_client = kubernetes_client if kubernetes_client else KubernetesClient()

    def list(self, namespace):
        command = 'helm list -o yaml -n %s' % namespace
        result = subprocess.check_output(command, shell=True)
        releases = YAML().load(result)
        for release in releases:
            del(release['updated']) # We already have this as a datetime object.
        return releases

    def values(self, namespace, name):
        command = 'helm get values -o yaml -n %s %s' % (namespace, name)
        result = subprocess.check_output(command, shell=True)
        return YAML().load(result)

    def install(self, namespace, name, chart_name, values_file, wait=True, timeout='20m'):
        command = 'helm upgrade -i %s %s %s -n %s -f %s %s %s' % ('--insecure-skip-tls-verify' if os.environ.get('VIRTUAL_ENV') else '', # XXX Do not verify if running in virtual environment.
                                                                  '--atomic --wait' if wait else '',
                                                                  ('--timeout %s' % timeout) if timeout else '',
                                                                  namespace,
                                                                  values_file,
                                                                  name,
                                                                  chart_name)
        subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)

    def uninstall(self, namespace, name, wait=True, timeout='20m'):
        command = 'helm uninstall %s %s -n %s %s' % ('--wait' if wait else '',
                                                     ('--timeout %s' % timeout) if timeout else '',
                                                     namespace,
                                                     name)
        subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
