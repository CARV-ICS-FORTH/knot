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
import string
import yaml

from django.conf import settings

from .inject import inject_hostpath_volumes, inject_service_label, inject_ingress_auth


class Template(object):
    def __init__(self, data):
        self._name = ''
        self._description = ''
        self._singleton = False
        self._mount = True
        self._variables = None
        self._values = {}

        self._template = []
        for part in yaml.safe_load_all(data):
            if part['kind'] == 'Template' and 'name' in part and 'variables' in part:
                self._name = part['name']
                self._description = part.get('description', '')
                self._singleton = part.get('singleton', False)
                self._mount = part.get('mount', True)
                self._variables = part['variables']
            else:
                self._template.append(part)
        if self._variables is None:
            raise ValueError('Can not find variables in template file')

        for variable in self._variables:
            if 'name' not in variable or 'default' not in variable:
                raise ValueError('Missing necessary variable attributes in template file')
            self._values[variable['name']] = variable['default']

        keys = list(self._values.keys())
        if 'NAME' not in keys:
            raise ValueError('Missing name variable in template file')

    def __getattr__(self, name):
        if not name.startswith('_') and name in self._values:
            return self._values[name]
        raise AttributeError('Template has no variable named "%s"' % name)

    def __setattr__(self, name, value):
        if not name.startswith('_') and name in self._values:
            self._values[name] = value
            return
        super().__setattr__(name, value)

    def inject_hostpath_volumes(self, volumes):
        inject_hostpath_volumes(self._template, volumes)

    def inject_service_label(self, template=None):
        inject_service_label(self._template, template=template, values=self._values)

    def inject_ingress_auth(self, secret, realm, redirect_ssl=False):
        inject_ingress_auth(self._template, secret, realm, redirect_ssl=redirect_ssl)

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def singleton(self):
        return self._singleton

    @property
    def mount(self):
        return self._mount

    @property
    def variables(self):
        return self._variables

    @property
    def values(self):
        return self._values

    @property
    def yaml(self):
        return string.Template(yaml.safe_dump_all(self._template)).safe_substitute(self._values)

    def format(self):
        return {'name': self._name,
                'description': self._description,
                'singleton': self._singleton,
                'mount': self._mount,
                'variables': self._variables}

    def __str__(self):
        if self._description:
            return '%s: %s' % (self._name, self._description)
        return self._name

class FileTemplate(Template):
    def __init__(self, filename):
        self._filename = filename

        try:
            with open(os.path.join(settings.SERVICE_TEMPLATE_DIR, filename), 'rb') as f:
                data = f.read()
        except:
            raise ValueError('Can not read template "%s"' % filename)

        super().__init__(data)

    @property
    def filename(self):
        return self._filename

    def inject_service_label(self):
        super().inject_service_label(template=self._filename)

    def format(self):
        result = super().format()
        result.update({'filename': self._filename})
        return result
