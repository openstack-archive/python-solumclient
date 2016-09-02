# Copyright (c) 2014 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

from oslo_log import log as logging

from solumclient import client as solum_client
from solumclient.common import exc
from solumclient.openstack.common import cliutils


class CommandsBase(object):
    """Base command parsing class."""
    parser = None
    solum = None
    json_output = False
    verify = True

    def __init__(self, parser):
        self.parser = parser

        self._get_global_flags()

        try:
            self._get_auth_flags()
        except exc.CommandError as ce:
            print(self.__doc__)
            print("ERROR: %s" % ce.message)
            return

        self.parser.add_argument('action',
                                 default='help',
                                 help='Action to perform on resource')

        parsed, _ = self.parser.parse_known_args()
        action = vars(parsed).get('action')

        client_args = vars(parsed)
        client_args.pop('insecure', None)
        client_args['verify'] = self.verify
        if 'os_auth_token' in client_args:
            del client_args['os_auth_token']

        self.client = solum_client.get_client(parsed.solum_api_version,
                                              **client_args)

        if action in self._actions:
            try:
                return self._actions[action]()
            except exc.CommandError as ce:
                print("ERROR: %s" % ce.message)
        else:
            print(self.__doc__)

    def _get_auth_flags(self):
        self.parser.add_argument('--os-username',
                                 default=env('OS_USERNAME'),
                                 help='Defaults to env[OS_USERNAME]')

        self.parser.add_argument('--os-password',
                                 default=env('OS_PASSWORD'),
                                 help='Defaults to env[OS_PASSWORD]')

        self.parser.add_argument('--os-tenant-name',
                                 default=env('OS_TENANT_NAME'),
                                 help='Defaults to env[OS_TENANT_NAME]')

        self.parser.add_argument('--os-auth-url',
                                 default=env('OS_AUTH_URL'),
                                 help='Defaults to env[OS_AUTH_URL]')

        self.parser.add_argument('--os-auth-token',
                                 default=env('OS_AUTH_TOKEN'),
                                 help='Defaults to env[OS_AUTH_TOKEN]')

        self.parser.add_argument('--solum-url',
                                 default=env('SOLUM_URL'),
                                 help='Defaults to env[SOLUM_URL]')

        api_version = env('SOLUM_API_VERSION', default='1')
        self.parser.add_argument('--solum-api-version',
                                 default=api_version,
                                 help='Defaults to env[SOLUM_API_VERSION] '
                                      'or 1')

        parsed, _ = self.parser.parse_known_args()

        client_args = vars(parsed)

        if not parsed.os_auth_token:
            # Remove arguments that are not to be passed to the client in this
            # case.
            del client_args['os_auth_token']

            if not parsed.os_username:
                raise exc.CommandError("You must provide a username via "
                                       "either --os-username or via "
                                       "env[OS_USERNAME]")

            if not parsed.os_password:
                raise exc.CommandError("You must provide a password via "
                                       "either --os-password or via "
                                       "env[OS_PASSWORD]")

            if not parsed.os_tenant_name:
                raise exc.CommandError("You must provide a tenant_name via "
                                       "either --os-tenant-name or via "
                                       "env[OS_TENANT_NAME]")

            if not parsed.os_auth_url:
                raise exc.CommandError("You must provide an auth url via "
                                       "either --os-auth-url or via "
                                       "env[OS_AUTH_URL]")

    @property
    def _actions(self):
        """Action handler."""
        return dict((attr, getattr(self, attr))
                    for attr in dir(self)
                    if not attr.startswith('_')
                    and callable(getattr(self, attr)))

    def _get_global_flags(self):
        """Get global flags."""
        # Good location to add_argument() global options like --verbose
        self.parser.add_argument('--json',
                                 action='store_true',
                                 help='JSON formatted output')
        self.parser.add_argument('-k', '--insecure',
                                 action='store_true',
                                 help='Explicitly allow the client to perform'
                                      ' \"insecure SSL\" (https) requests.'
                                      ' The server\'s certificate will not be'
                                      ' verified against any certificate'
                                      ' authorities. This option should be'
                                      ' used with caution.')
        self.parser.add_argument('-d', '--debug',
                                 action='store_true',
                                 help='Print out request and response '
                                      'details.')
        args, _ = self.parser.parse_known_args()
        if args.json:
            self.json_output = True
        if args.insecure:
            self.verify = False
        if args.debug:
            logging.basicConfig(
                format="%(levelname)s (%(module)s) %(message)s",
                level=logging.DEBUG)
            logging.getLogger('iso8601').setLevel(logging.WARNING)
            urllibpool = 'urllib3.connectionpool'
            logging.getLogger(urllibpool).setLevel(logging.WARNING)

    def _sanitized_fields(self, fields):
        def allowed(field):
            if field.startswith('_'):
                return False
            if field == 'manager':
                return False
            if field == 'artifacts':
                return False
            return True
        return [f for f in fields
                if allowed(f)]

    def _print_dict(self, obj, fields, dict_property="Property", wrap=0):
        fields = self._sanitized_fields(fields)
        try:
            # datsun180b: I have no idea why, but following a PATCH
            # app resources need to have this evaluated once or else
            # the subset assignment below fails.
            obj.attrs
        except TypeError:
            pass
        except AttributeError:
            pass
        subset = dict([(f, getattr(obj, f, '')) for f in fields])
        if self.json_output:
            print(json.dumps(subset, indent=2, sort_keys=True))
        else:
            cliutils.print_dict(subset, dict_property, wrap)

    def _print_list(self, objs, fields, formatters=None, sortby_index=0,
                    mixed_case_fields=None, field_labels=None):
        fields = self._sanitized_fields(fields)
        if self.json_output:
            subsets = [dict([(f, getattr(obj, f, '')) for f in fields])
                       for obj in objs]
            print(json.dumps(subsets, indent=2, sort_keys=True))
        else:
            cliutils.print_list(objs, fields, formatters, sortby_index,
                                mixed_case_fields, field_labels)


class NoSubCommands(CommandsBase):
    """Command parsing class that lacks an 'action'."""
    parser = None
    solum = None
    json_output = False
    verify = True

    def __init__(self, parser):
        self.parser = parser

        self._get_global_flags()

        try:
            self._get_auth_flags()
        except exc.CommandError as ce:
            print(self.__doc__)
            print("ERROR: %s" % ce.message)
            return

        parsed, _ = self.parser.parse_known_args()

        client_args = vars(parsed)
        client_args.pop('insecure', None)
        client_args['verify'] = self.verify
        if 'os_auth_token' in client_args:
            del client_args['os_auth_token']

        self.client = solum_client.get_client(parsed.solum_api_version,
                                              **client_args)

        return self.info()

    def info(self):
        pass


def env(*vars, **kwargs):
    """Search for the first defined of possibly many env vars

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


def filter_ready_lps(lp_list):
    filtered_list = []
    for lp in lp_list:
        if lp.status == 'READY':
            filtered_list.append(lp)

    return filtered_list
