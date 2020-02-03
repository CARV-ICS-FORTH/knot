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

import yaml

from string import Template


class Gene(object):
    def __init__(self, data):
        self._parts = yaml.safe_load_all(data)
        self._template = []
        self._name = ''
        self._description = ''
        self._variables = None
        self._values = {}

        for part in self._parts:
            if part['kind'] == 'Gene' and 'name' in part and 'variables' in part:
                self._name = part['name']
                self._description = part.get('description', '')
                self._variables = part['variables']
            else:
                self._template.append(part)
        if self._variables is None:
            raise ValueError('Can not find variables in gene file')

        for variable in self._variables:
            if not 'name' in variable or not 'default' in variable:
                raise ValueError('Missing necessary variable attributes in gene file')
            self._values[variable['name']] = variable['default']

    def __getattr__(self, name):
        if not name.startswith('_') and name in self._values:
            return self._values[name]
        raise AttributeError('Gene has no variable named "%s"' % name)

    def __setattr__(self, name, value):
        if not name.startswith('_') and name in self._values:
            self._values[name] = value
            return
        super().__setattr__(name, value)

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def variables(self):
        return self._variables

    @property
    def values(self):
        return self._values

    @property
    def yaml(self):
        return Template(yaml.safe_dump_all(self._template)).safe_substitute(self._values)

    def __str__(self):
        if self._description:
            return '%s: %s' % (self._name, self._description)
        return self._name
