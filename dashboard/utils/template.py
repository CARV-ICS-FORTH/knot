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

from .inject import inject_volumes, inject_service_details, inject_ingress_auth, inject_no_datasets_label


class Template(object):
    def __init__(self, data):
        self._data = data if type(data) == str else data.decode()
        self._name = ''
        self._description = ''
        self._singleton = False
        self._auth = True
        self._datasets = False
        self._variables = None
        self._values = {}

        self._template = []
        for part in yaml.safe_load_all(data):
            if part['kind'] == 'Template' and 'name' in part and 'variables' in part:
                self._name = part['name']
                self._description = part.get('description', '')
                self._singleton = part.get('singleton', False)
                self._auth = part.get('auth', True)
                self._datasets = part.get('datasets', True)
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

    def inject_volumes(self, volumes, add_api_settings=False, is_datasets=False):
        inject_volumes(self._template, volumes, add_api_settings=add_api_settings, is_datasets=is_datasets)

    def inject_service_details(self, template=None):
        inject_service_details(self._template, template=template, values=self._values)

    def inject_ingress_auth(self, auth_config, redirect_ssl=False):
        inject_ingress_auth(self._template, auth_config, redirect_ssl=redirect_ssl)

    def inject_no_datasets_label(self):
        inject_no_datasets_label(self._template)

    @property
    def data(self):
        return self._data

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
    def auth(self):
        return self._auth

    @property
    def datasets(self):
        return self._datasets

    @property
    def variables(self):
        return self._variables

    @property
    def values(self):
        return self._values

    @property
    def yaml(self):
        return string.Template(yaml.safe_dump_all(self._template)).safe_substitute(self._values)

    def format(self, include_data=False):
        result = {'name': self._name,
                  'description': self._description,
                  'singleton': self._singleton,
                  'auth': self._auth,
                  'datasets': self._datasets,
                  'variables': self._variables}
        if include_data:
            result.update({'data': self._data})
        return result

    def __str__(self):
        if self._description:
            return '%s: %s' % (self._name, self._description)
        return self._name

class ServiceTemplate(Template):
    def __init__(self, data, identifier=None):
        super().__init__(data)

        self._identifier = identifier

    @property
    def identifier(self):
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        self._identifier = value

    def inject_service_details(self):
        super().inject_service_details(template=self.identifier)

    def format(self, include_data=False):
        result = super().format(include_data=include_data)
        result.update({'id': self.identifier})
        return result

class FileTemplate(ServiceTemplate):
    def __init__(self, path):
        self._path = path
        self._filename = os.path.basename(path)

        try:
            with open(path, 'rb') as f:
                data = f.read()
        except:
            raise ValueError('Can not read template "%s"' % path)

        super().__init__(data, identifier=self._filename.split('.')[0])

    @property
    def filename(self):
        return self._filename

    def format(self, include_data=False):
        result = super().format(include_data=include_data)
        result.update({'filename': self._filename})
        return result
