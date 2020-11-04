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

from urllib.parse import urlparse


class KubernetesClient(object):
    def __init__(self):
        self._config_loaded = False
        self._core_client = None
        self._extensions_client = None
        self._custom_objects_client = None

    def _load_config(self):
        if self._config_loaded:
            return
        try:
            kubernetes.config.load_kube_config()
        except:
            kubernetes.config.load_incluster_config()
        self._config_loaded = True

    @property
    def core_client(self):
        if not self._core_client:
            self._load_config()
            self._core_client = kubernetes.client.CoreV1Api()
        return self._core_client

    @property
    def extensions_client(self):
        if not self._extensions_client:
            self._load_config()
            self._extensions_client = kubernetes.client.ExtensionsV1beta1Api()
        return self._extensions_client

    @property
    def custom_objects_client(self):
        if not self._custom_objects_client:
            self._load_config()
            self._custom_objects_client = kubernetes.client.CustomObjectsApi()
        return self._custom_objects_client

    @property
    def host(self):
        return self.core_client.api_client.configuration.host

    def list_namespaces(self):
        return self.core_client.list_namespace().items

    def list_services(self, namespace, label_selector):
        return self.core_client.list_namespaced_service(namespace=namespace, label_selector=label_selector).items

    def list_ingresses(self, namespace):
        return self.extensions_client.list_namespaced_ingress(namespace=namespace).items

    def list_crds(self, group, version, namespace, plural):
        return self.custom_objects_client.list_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural)['items']

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

    def apply_crd(self, group, version, namespace, plural, yaml):
        return self.custom_objects_client.create_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural, body=yaml)

    def delete_crd(self, group, version, namespace, plural, name):
        return self.custom_objects_client.delete_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural, name=name, body={})

    def delete_secret(self, namespace, name):
        os.system('kubectl delete -n %s secret %s' % (namespace, name))

    def update_secret(self, namespace, name, literal):
        self.delete_secret(namespace, name)
        if os.system('kubectl create -n %s secret generic %s --from-literal=\'%s\'' % (namespace, name, literal)) < 0:
            raise SystemError('Can not create secret')

    def create_docker_registry_secret(self, namespace, registry_url, email):
        url = urlparse(registry_url)
        if not url.username or not url.password:
            return

        server = '%s://%s:%s' % (url.scheme, url.hostname, url.port)
        os.system('kubectl create secret docker-registry docker-registry-secret -n %s --docker-server="%s" --docker-username="%s" --docker-password="%s" --docker-email="%s"' % (namespace, server, url.username, url.password, email))
        os.system('kubectl patch serviceaccount default -n %s -p \'{"imagePullSecrets": [{"name": "docker-registry-secret"}]}\'' % namespace)

    def exec_command_in_pod(self, namespace, label_selector, command, all_pods=False):
        result = []
        for pod in self.core_client.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items:
            result.append(kubernetes.stream.stream(self.core_client.connect_get_namespaced_pod_exec,
                                                   pod.metadata.name,
                                                   namespace,
                                                   command=command,
                                                   stderr=True,
                                                   stdin=False,
                                                   stdout=True,
                                                   tty=False))
            if not all_pods:
                break
        return result

    def add_namespace_label(self, namespace, label):
        body = {"metadata": {"labels": {label: "enabled"}}}
        self.core_client.patch_namespace(namespace, body)

    def delete_namespace_label(self, namespace, label):
        body = {"metadata": {"labels": {label: None}}}
        try:
            self.core_client.patch_namespace(namespace, body)
        except:
            pass

    def get_datasets(self, namespace):
        contents = []
        try:
            for dataset in self.list_crds(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=namespace, plural='datasets'):
                try:
                    dataset_type = dataset['spec']['local']['type']
                except:
                    continue
                if dataset_type == 'COS':
                    dataset_type = 'S3'
                    endpoint = dataset['spec']['local']['endpoint'] + '/' + dataset['spec']['local']['bucket']
                # elif dataset_type == 'HOST':
                #     dataset_type = 'HostPath'
                #     endpoint = dataset['spec']['local']['path']
                else:
                    continue

                contents.append({'name': dataset['metadata']['name'],
                                 'type': dataset_type,
                                 'endpoint': endpoint})
        except:
            pass

        return contents
