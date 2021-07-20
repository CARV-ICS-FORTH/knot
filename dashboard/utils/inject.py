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

from urllib.parse import urlparse


def inject_volumes(yaml_data, file_domains, add_api_settings=False, is_datasets=False):
    def add_volumes_to_spec(spec, no_datasets):
        # Add volumes.
        if 'volumes' not in spec:
            spec['volumes'] = []
        existing_names = [v['name'] for v in spec['volumes']]
        for file_domain in file_domains.values():
            if file_domain.volume_name in existing_names:
                continue
            spec['volumes'].append({'name': file_domain.volume_name,
                                    'persistentVolumeClaim': {'claimName': file_domain.volume_name}})
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
            for file_domain in file_domains.values():
                if file_domain.volume_name in existing_names:
                    continue
                container['volumeMounts'].append({'name': file_domain.volume_name,
                                                  'mountPath': file_domain.mount_dir})
            if add_api_settings and 'karvdash-api-volume' not in existing_names:
                container['volumeMounts'].append({'name': 'karvdash-api-volume',
                                                  'mountPath': '/var/lib/karvdash'})

    for part in yaml_data:
        no_datasets = False
        try:
            if part['kind'] == 'Deployment':
                spec = part['spec']['template']['spec']
                try:
                    if part['spec']['template']['metadata']['labels']['karvdash-no-datasets'] == 'true':
                        no_datasets = True
                except:
                    pass
            elif part['kind'] == 'Pod':
                spec = part['spec']
                try:
                    if part['metadata']['labels']['karvdash-no-datasets'] == 'true':
                        no_datasets = True
                except:
                    pass
            else:
                continue
        except:
            continue
        if not spec or 'containers' not in spec:
            continue
        if no_datasets and is_datasets:
            continue
        add_volumes_to_spec(spec, no_datasets)

def validate_hostpath_volumes(yaml_data, file_domains, other_allowed_paths=[]):
    allowed_paths = [urlparse(file_domain.url).path for file_domain in file_domains.values() if file_domain.url.startswith('file://')]
    allowed_paths += other_allowed_paths

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
            if 'nfs' in volume:
                return False
            if 'hostPath' not in volume or 'path' not in volume['hostPath']:
                continue
            if volume['hostPath']['path'] not in allowed_paths:
                return False

    return True

def inject_service_details(yaml_data, template=None, values=None):
    for part in yaml_data:
        if part.get('kind') == 'Service':
            try:
                if part['metadata']['labels']['karvdash-hidden'] == 'true':
                    continue
            except:
                pass
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
            return # Only mark the first service.

def inject_ingress_auth(yaml_data, auth_config, redirect_ssl=False):
    for part in yaml_data:
        if part.get('kind') == 'Ingress':
            if 'metadata' not in part:
                part['metadata'] = {}
            if 'annotations' not in part['metadata']:
                part['metadata']['annotations'] = {}
            if 'vouch_url' in auth_config:
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-signin'] = '%s/login?url=$scheme://$http_host$request_uri&vouch-failcount=$auth_resp_failcount&X-Vouch-Token=$auth_resp_jwt&error=$auth_resp_err' % auth_config['vouch_url']
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-url'] = '%s/validate' % auth_config['vouch_url']
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-response-headers'] = 'X-Vouch-User'
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-snippet'] = '\n'.join(('auth_request_set $auth_resp_jwt $upstream_http_x_vouch_jwt;',
                                                                                                         'auth_request_set $auth_resp_err $upstream_http_x_vouch_err;',
                                                                                                         'auth_request_set $auth_resp_failcount $upstream_http_x_vouch_failcount;'))
            else:
                # Fallback to basic HTTP authentication.
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-type'] = 'basic'
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-secret'] = auth_config['secret']
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/auth-realm'] = auth_config['realm']
            if redirect_ssl:
                part['metadata']['annotations']['nginx.ingress.kubernetes.io/force-ssl-redirect'] = 'true'

def inject_no_datasets_label(yaml_data):
    for part in yaml_data:
        try:
            if part['kind'] == 'Deployment':
                metadata_parent = part['spec']['template']
            elif part['kind'] == 'Pod':
                metadata_parent = part
            else:
                continue
        except:
            continue
        if 'metadata' not in metadata_parent:
            metadata_parent['metadata'] = {}
        if 'labels' not in metadata_parent['metadata']:
            metadata_parent['metadata']['labels'] = {}
        metadata_parent['metadata']['labels']['karvdash-no-datasets'] = 'true'
