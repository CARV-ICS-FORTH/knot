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
import tempfile

import kubernetes.client
import kubernetes.config
import kubernetes.stream

from urllib.parse import urlparse


class KubernetesClient(object):
    def __init__(self):
        self._config_loaded = False
        self._core_client = None
        self._networking_client = None
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
    def networking_client(self):
        if not self._networking_client:
            self._load_config()
            self._networking_client = kubernetes.client.NetworkingV1Api()
        return self._networking_client

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

    def list_config_maps(self, namespace):
        return self.core_client.list_namespaced_config_map(namespace=namespace).items

    def list_service_accounts(self, namespace):
        return self.core_client.list_namespaced_service_account(namespace=namespace).items

    def list_services(self, namespace):
        return self.core_client.list_namespaced_service(namespace=namespace).items

    def list_ingresses(self, namespace):
        return self.networking_client.list_namespaced_ingress(namespace=namespace).items

    def list_crds(self, group, version, namespace, plural):
        return self.custom_objects_client.list_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural)['items']

    def list_secrets(self, namespace):
        return self.core_client.list_namespaced_secret(namespace=namespace).items

    def list_persistent_volume_claims(self, namespace):
        return self.core_client.list_namespaced_persistent_volume_claim(namespace=namespace).items

    def apply_yaml_file(self, yaml_file, namespace=None):
        command = 'kubectl apply -f %s' % yaml_file
        if namespace:
            command += ' -n %s' % namespace
        # if os.system(command) != 0:
        #     raise SystemError('Can not apply service file')
        os.system(command)

    def apply_yaml_data(self, yaml_data, namespace=None):
        with tempfile.NamedTemporaryFile() as f:
            f.write(yaml_data)
            f.seek(0)
            self.apply_yaml_file(f.name, namespace)

    def delete_yaml_file(self, yaml_file, namespace=None):
        command = 'kubectl delete -f %s' % yaml_file
        if namespace:
            command += ' -n %s' % namespace
        # if os.system(command) != 0:
        #     raise SystemError('Can not delete service file')
        os.system(command)

    def delete_yaml_data(self, yaml_data, namespace=None):
        with tempfile.NamedTemporaryFile() as f:
            f.write(yaml_data)
            f.seek(0)
            self.delete_yaml_file(f.name, namespace)

    def apply_crd(self, group, version, namespace, plural, yaml):
        return self.custom_objects_client.create_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural, body=yaml)

    def delete_crd(self, group, version, namespace, plural, name):
        return self.custom_objects_client.delete_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural, name=name, body={})

    def delete_secret(self, namespace, name):
        command = 'kubectl delete secret %s' % name
        if namespace:
            command += ' -n %s' % namespace
        # if os.system(command) != 0:
        #     raise SystemError('Can not delete service file')
        os.system(command)

    def update_secret(self, namespace, name, literals):
        self.delete_secret(namespace, name)
        command = 'kubectl create secret generic %s' % name
        if namespace:
            command += ' -n %s' % namespace
        for literal in literals:
            command += ' --from-literal=\'%s\'' % literal
        # if os.system(command) != 0:
        #     raise SystemError('Can not delete service file')
        os.system(command)

    def update_registry_secret(self, namespace, registry_url, email):
        if not registry_url:
            return

        url = urlparse(registry_url)
        if not url.username or not url.password:
            return

        if 'docker-registry-secret' not in [s.metadata.name for s in self.list_secrets(namespace)]:
            os.system('kubectl patch serviceaccount default -n %s -p \'{"imagePullSecrets": [{"name": "docker-registry-secret"}]}\'' % namespace)

        self.delete_secret(namespace, 'docker-registry-secret')
        server = '%s://%s:%s' % (url.scheme, url.hostname, url.port)
        os.system('kubectl create secret docker-registry docker-registry-secret -n %s --docker-server="%s" --docker-username="%s" --docker-password="%s" --docker-email="%s"' % (namespace, server, url.username, url.password, email))

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
