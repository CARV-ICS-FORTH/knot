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
import requests

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser


class API:
    """Python interface to the Karvdash API.

    :param config_path: file containing configuration options for the API endpoint
    :type config_path: string

    The provided config file should have the following structure (example values shown)::

        [Karvdash]
        base_url = http://karvdash.default.svc/api
        token = 8e41faf30b7bee20725a49bd73bba680055b95c1

    If no config file is set, the following paths are tried in order: ``~/.karvdash/config.ini``, ``/var/lib/karvdash/config.ini``.
    """

    def __init__(self, config_path=None):
        self.config_path = config_path if config_path else self._get_config_path()
        self.base_url, self.token = self._get_configuration(self.config_path)

    def _get_config_path(self):
        try:
            return os.environ['KARVDASH_CONFIG']
        except KeyError:
            pass

        config_paths = [os.path.join(os.environ['HOME'], '.karvdash', 'config.ini'),
                        '/var/lib/karvdash/config.ini']
        for config_path in config_paths:
            if os.access(config_path, os.F_OK):
                return config_path

        return config_paths[0]

    def _get_configuration(self, config_path):
        config = ConfigParser()
        config.read(config_path)
        base_url = config.get('Karvdash', 'base_url').rstrip('/')
        token = config.get('Karvdash', 'token').strip()
        return base_url, token

    @property
    def _headers(self):
        return {'Authorization': 'Token %s' % self.token.lower()}

    def list_services(self):
        """List running services.

        :returns: A list of services

        Each service is represented with a dictionary containing the following keys:

        ============  ================  ================================================
        Key           Type              Description
        ------------  ----------------  ------------------------------------------------
        ``name``      <string>          The service name
        ``url``       <string>          The URL to access the service frontend
        ``created``   <string>          When the service was created (not included

                                        in response to service create calls)
        ``actions``   <boolean>         ``True`` if service can be deleted
        ``template``  <dictionary>      Service template information
        ============  ================  ================================================

        For a list of keys in the template dictionary, consult
        the ``list_services()`` function documentation.
        """

        r = requests.get(self.base_url + '/services/', headers=self._headers)
        r.raise_for_status()
        return r.json()

    def create_service(self, identifier, variables):
        """Create/start a service.

        :param identifier: the template identifier
        :param variables: template variables as key-value pairs (provide at least a ``name`` key)
        :type identifier: string
        :type variables: dictionary
        :returns: The service created
        """

        parameters = {k.upper(): v for k, v in variables.items()}
        parameters['id'] = identifier
        r = requests.post(self.base_url + '/services/', json=parameters, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def exec_service(self, name, command, all_pods=False):
        """Execute a command at service pods.

        :param command: the command to execute
        :param all_pods: execute command in all pods
        :type command: list
        :type all_pods: boolean
        :returns: A list of results
        """

        parameters = {'command': command,
                      'all_pods': 1 if all_pods else 0}
        r = requests.post(self.base_url + '/services/%s/' % name, json=parameters, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def delete_service(self, name):
        """Delete/stop a running service.

        :param name: the service to delete
        :type name: string
        """

        r = requests.delete(self.base_url + '/services/%s/' % name, headers=self._headers)
        r.raise_for_status()

    def list_templates(self):
        """List available templates.

        :returns: A list of templates

        Each template is represented with a dictionary containing the following keys:

        ===============  ================  ================================================================
        Key              Type              Description
        ---------------  ----------------  ----------------------------------------------------------------
        ``id``           <string>          The template identifier
        ``name``         <string>          The template name as shown in the dashboard
        ``description``  <string>          The template description as shown in the dashboard
        ``singleton``    <boolean>         ``True`` if only one instance can be running
        ``auth``         <boolean>         ``True`` if HTTP authentication should be added by the ingress
        ``variables``    <dictionary>      Template variables
        ``values``       <dictionary>      Instance values for template variables (included
                                           when template is returned as part of a service)
        ``filename``     <string>          The template filename (included for system templates)
        ``data``         <string>          The actual template (included when requesting a single template)
        ===============  ================  ================================================================
        """

        r = requests.get(self.base_url + '/templates/', headers=self._headers)
        r.raise_for_status()
        return r.json()

    def add_template(self, data):
        """Add a template.

        :param data: the template in YAML format
        :type data: string
        :returns: The template created
        """

        parameters = {'data': data if type(data) == str else data.decode()}
        r = requests.post(self.base_url + '/templates/', json=parameters, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def get_template(self, identifier):
        """Get template data.

        :param identifier: the template identifier
        :type identifier: string
        :returns: The template including data
        """

        r = requests.get(self.base_url + '/templates/%s/' % identifier, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def remove_template(self, identifier):
        """Remove a template.

        :param identifier: the template identifier
        :type identifier: string
        """

        r = requests.delete(self.base_url + '/templates/%s/' % identifier, headers=self._headers)
        r.raise_for_status()
