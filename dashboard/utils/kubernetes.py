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

import kubernetes.client
import kubernetes.config
import kubernetes.stream


class KubernetesClient(object):
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            try:
                kubernetes.config.load_kube_config()
            except:
                kubernetes.config.load_incluster_config()
            self._client = kubernetes.client.CoreV1Api()
        return self._client

    @property
    def host(self):
        return self.client.api_client.configuration.host

    def list_namespaces(self):
        return self.client.list_namespace().items

    def list_services(self, namespace, label_selector):
        return self.client.list_namespaced_service(namespace=namespace, label_selector=label_selector).items

    def apply_yaml(self, yaml_file, namespace=None):
        command = 'kubectl apply -f %s' % yaml_file
        if namespace:
            command += ' -n %s' % namespace
        if os.system(command) < 0:
            raise SystemError('Can not apply service file')

    def delete_yaml(self, yaml_file, namespace=None):
        command = 'kubectl delete -f %s' % yaml_file
        if namespace:
            command += ' -n %s' % namespace
        if os.system(command) < 0:
            raise SystemError('Can not delete service file')

    def delete_secret(self, namespace, name):
        os.system('kubectl delete -n %s secret %s' % (namespace, name))

    def update_secret(self, namespace, name, literal):
        self.delete_secret(namespace, name)
        if os.system('kubectl create -n %s secret generic %s --from-literal=\'%s\'' % (namespace, name, literal)) < 0:
            raise SystemError('Can not create secret')

    def run_command_in_pod(self, namespace, label_selector, command):
        result = []
        for pod in self.client.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items:
            result.append(kubernetes.stream.stream(self.client.connect_get_namespaced_pod_exec,
                                                   pod.metadata.name,
                                                   namespace,
                                                   command=command,
                                                   stderr=True,
                                                   stdin=False,
                                                   stdout=True,
                                                   tty=False))
        return result
