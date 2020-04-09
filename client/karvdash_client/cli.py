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

import sys
import argparse

from pprint import pprint

from .api import API


def cmd_list_services(api, args):
    pprint(api.list_services())

def cmd_create_service(api, args):
    variables = dict(map(lambda s: s.split('='), args.variables))
    pprint(api.create_service(args.filename, variables))

def cmd_exec_service(api, args):
    if not args.args:
        return
    response = api.exec_service(args.name, args.args, args.all_pods)
    sys.stdout.write(''.join(response['result'])) # No newline at the end

def cmd_delete_service(api, args):
    api.delete_service(args.name)

def cmd_list_templates(api, args):
    pprint(api.list_templates())

def cmd_inject(api, args):
    with open(args.filename, 'rb') as fp:
        print(api.inject(fp.read()))

def main(cmd=None):
    parser = argparse.ArgumentParser(description='Karvdash API client command line tool')
    # parser.add_argument('-d', '--debug', action='store_true', help='Print debug info')
    parser.add_argument('--config', help='Karvdash API client configuration file')
    subprasers = parser.add_subparsers(dest='command', title='API command')

    list_services = subprasers.add_parser('list_services', help='List running services')
    list_services.set_defaults(func=cmd_list_services)

    create_service = subprasers.add_parser('create_service', help='Create a service from a template')
    create_service.add_argument('filename', help='Template filename')
    create_service.add_argument('variables', nargs='+', help='Template variables as key=value pairs (provide at least a "name")')
    create_service.set_defaults(func=cmd_create_service)

    exec_service = subprasers.add_parser('exec_service', help='Execute a command at a running service')
    exec_service.add_argument('-a', '--all-pods', action='store_true', help='Execute in all pods')
    exec_service.add_argument('name', help='Service name')
    exec_service.add_argument('args', nargs=argparse.REMAINDER, help='Command and arguments to execute')
    exec_service.set_defaults(func=cmd_exec_service)

    delete_service = subprasers.add_parser('delete_service', help='Delete a running service')
    delete_service.add_argument('name', help='Service name')
    delete_service.set_defaults(func=cmd_delete_service)

    list_templates = subprasers.add_parser('list_templates', help='List available templates')
    list_templates.set_defaults(func=cmd_list_templates)

    inject = subprasers.add_parser('inject', help='Inject storage directives to YAML file')
    inject.add_argument('filename', help='YAML file')
    inject.set_defaults(func=cmd_inject)

    args = parser.parse_args(cmd)
    if args.command:
        api = API(args.config)
        args.func(api, args)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
