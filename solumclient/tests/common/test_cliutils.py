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

import fixtures
import mock

from solumclient import client as solum_client
from solumclient.common import cli_utils
import solumclient.solum
from solumclient.tests import base


class TestCli_Utils(base.TestCase):
    "Test commandbase"
    scenarios = [
        ('username', dict(
            fake_env={'OS_USERNAME': 'username',
                      'OS_PASSWORD': 'password',
                      'OS_TENANT_NAME': 'tenant_name',
                      'OS_AUTH_URL': 'http://no.where'},
            output={'solum_api_version': '1',
                    'os_username': 'username',
                    'solum_url': '',
                    'os_tenant_name': 'tenant_name',
                    'os_auth_url': 'http://no.where',
                    'os_password': 'password',
                    'action': 'create',
                    'json': False,
                    'verify': True,
                    'debug': False
                    })),
        ('token', dict(
            fake_env={'OS_AUTH_TOKEN': '123456',
                      'SOLUM_URL': 'http://10.0.2.15:9777'},
            output={'os_auth_url': '',
                    'solum_url': 'http://10.0.2.15:9777',
                    'solum_api_version': '1',
                    'os_username': '',
                    'os_tenant_name': '',
                    'os_password': '',
                    'action': 'create',
                    'json': False,
                    'verify': True,
                    'debug': False
                    })),
        ('solum_url_with_no_token', dict(
            fake_env={'OS_USERNAME': 'username',
                      'OS_PASSWORD': 'password',
                      'OS_TENANT_NAME': 'tenant_name',
                      'OS_AUTH_URL': 'http://no.where',
                      'SOLUM_URL': 'http://10.0.2.15:9777'},
            output={'os_auth_url': 'http://no.where',
                    'solum_url': 'http://10.0.2.15:9777',
                    'solum_api_version': '1',
                    'os_username': 'username',
                    'os_tenant_name': 'tenant_name',
                    'os_password': 'password',
                    'action': 'create',
                    'json': False,
                    'verify': True,
                    'debug': False
                    })),
    ]

    # Patch os.environ to avoid reading auth info
    # from environment or command line.
    def make_env(self, exclude=None):
        env = dict((k, v) for k, v in self.fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    def fake_argv(self):
        self.useFixture(fixtures.MonkeyPatch('sys.argv', ['foo', 'create']))

    @mock.patch.object(solum_client, "get_client")
    def test_env_parsing(self, mock_get_client):
        parser = solumclient.solum.PermissiveParser()

        self.make_env()
        self.fake_argv()
        FakeCommands(parser)
        mock_get_client.assert_called_once_with(
            self.output['solum_api_version'], **self.output)


class FakeCommands(cli_utils.CommandsBase):
    """Fake command class."""

    def create(self):
        """Fake Create Method."""
        return
