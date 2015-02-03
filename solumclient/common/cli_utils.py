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

import os

from solumclient.builder import client as builder_client
from solumclient import client as solum_client
from solumclient.common import exc


class CommandsBase(object):
    """Base command parsing class."""
    parser = None
    solum = None

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
        if 'os_auth_token' in client_args:
            del client_args['os_auth_token']

        self.bldclient = builder_client.get_client(parsed.solum_api_version,
                                                   **client_args)
        self.client = solum_client.get_client(parsed.solum_api_version,
                                              **client_args)

        if parsed.action in self._actions:
            try:
                return self._actions[action]()
            except exc.CommandError as ce:
                print(self.__doc__)
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
