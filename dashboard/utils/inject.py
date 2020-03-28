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

import json


def inject_hostpath_volumes(yaml_data, volumes):
    def add_volumes_to_spec(spec):
        # Add volumes.
        if 'volumes' not in spec:
            spec['volumes'] = []
        for name, variables in volumes.items():
            if not variables['dir'] or not variables['host_dir']:
                continue
            volume_name = 'karvdash-volume-%s' % name
            spec['volumes'].append({'name': volume_name, 'hostPath': {'path': variables['host_dir']}})

        # Mount volumes in containers.
        for container in spec['containers']:
            if 'volumeMounts' not in container:
                container['volumeMounts'] = []
            for name, variables in volumes.items():
                if not variables['dir'] or not variables['host_dir']:
                    continue
                volume_name = 'karvdash-volume-%s' % name
                container['volumeMounts'].append({'name': volume_name, 'mountPath': variables['dir']})

    for part in yaml_data:
        try:
            if part['kind'] == 'Deployment':
                spec = part['spec']['template']['spec']
            elif part['kind'] == 'Pod':
                spec = part['spec']
            else:
                continue
        except:
            continue
        if not spec or 'containers' not in spec:
            continue
        add_volumes_to_spec(spec)

def inject_service_label(yaml_data, template=None, values=None):
    for part in yaml_data:
        if part.get('kind') == 'Service':
            if 'metadata' not in part:
                part['metadata'] = {}
            if template:
                if 'labels' not in part['metadata']:
                    part['metadata']['labels'] = {}
                part['metadata']['labels']['karvdash-template'] = template
            if values:
                if 'annotations' not in part['metadata']:
                    part['metadata']['annotations'] = {}
                part['metadata']['annotations']['karvdash-values'] = json.dumps(values)

def inject_ingress_auth(yaml_data, secret, realm, redirect_ssl=False):
    for part in yaml_data:
        if part.get('kind') == 'Ingress':
            if 'metadata' not in part:
                part['metadata'] = {}
            if 'annotations' not in part['metadata']:
                part['metadata']['annotations'] = {}
            part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-type'] = 'basic'
            part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-secret'] = secret
            part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-realm'] = realm
            if redirect_ssl:
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/force-ssl-redirect'] = '"true"'
