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


def inject_hostpath_volumes(yaml_data, volumes, add_api_settings=False):
    def add_volumes_to_spec(spec):
        # Add volumes.
        if 'volumes' not in spec:
            spec['volumes'] = []
        existing_names = [v['name'] for v in spec['volumes']]
        for name, variables in volumes.items():
            if not variables['dir'] or not variables['host_dir']:
                continue
            volume_name = 'karvdash-volume-%s' % name
            if volume_name in existing_names:
                continue
            spec['volumes'].append({'name': volume_name,
                                    'hostPath': {'path': variables['host_dir']}})
        if add_api_settings and 'karvdash-api-volume' not in existing_names:
            spec['volumes'].append({'name': 'karvdash-api-volume',
                                    'configMap': {'name': 'karvdash-api',
                                                  'items': [{'key': 'config.ini',
                                                             'path': 'config.ini'}]}})

        # Mount volumes in containers.
        for container in spec['containers']:
            if 'volumeMounts' not in container:
                container['volumeMounts'] = []
            existing_names = [v['name'] for v in container['volumeMounts']]
            for name, variables in volumes.items():
                if not variables['dir'] or not variables['host_dir']:
                    continue
                volume_name = 'karvdash-volume-%s' % name
                if volume_name in existing_names:
                    continue
                container['volumeMounts'].append({'name': volume_name,
                                                  'mountPath': variables['dir']})
            if add_api_settings and 'karvdash-api-volume' not in existing_names:
                container['volumeMounts'].append({'name': 'karvdash-api-volume',
                                                  'mountPath': '/var/lib/karvdash'})

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

def validate_hostpath_volumes(yaml_data, volumes):
    allowed_paths = [variables['host_dir'] for name, variables in volumes.items() if 'host_dir' in variables]

    for part in yaml_data:
        try:
            if part['kind'] == 'Deployment':
                spec_volumes = part['spec']['template']['spec']['volumes']
            elif part['kind'] == 'Pod':
                spec_volumes = part['spec']['volumes']
            else:
                continue
        except:
            continue
        if not spec_volumes:
            continue
        for volume in spec_volumes:
            if 'hostPath' not in volume or 'path' not in volume['hostPath']:
                continue
            if volume['hostPath']['path'] not in allowed_paths:
                return False

    return True

def inject_service_details(yaml_data, template=None, values=None):
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

def inject_datasets(yaml_data, datasets):
    def add_datasets_to_metadata(template):
        if 'metadata' not in template:
            template['metadata'] = {}
        if 'labels' not in template['metadata']:
            template['metadata']['labels'] = {}
        for i, dataset in enumerate(datasets):
            template['metadata']['labels']['dataset.%d.id' % i] = dataset['name']
            template['metadata']['labels']['dataset.%d.useas' % i] = 'mount'

    for part in yaml_data:
        try:
            if part['kind'] == 'Deployment':
                template = part['spec']['template']
            elif part['kind'] == 'Pod':
                template = part
            else:
                continue
        except:
            continue
        add_datasets_to_metadata(template)
