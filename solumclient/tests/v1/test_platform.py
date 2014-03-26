# Copyright 2013 - Noorul Islam K M
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from solumclient.openstack.common.apiclient import fake_client
from solumclient.tests import base
from solumclient.v1 import client as sclient
from solumclient.v1 import platform


fixtures = {
    '/v1': {
        'GET': (
            {},
            {
                'uri': 'http://example.com/v1',
                'name': 'solum',
                'type': 'platform',
                'tags': ['solid'],
                'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
                'user_id': '55f41cf46df74320b9486a35f5d28a11',
                'description': 'solum native implementation',
                'implementation_version': '2014.1.1',
                'assemblies_uri': 'http://example.com:9777/v1/assemblies',
                'services_uri': 'http://example.com:9777/v1/services',
                'components_uri': 'http://example.com:9777/v1/components',
                'extenstions_uri': 'http://example.com:9777/v1/extenstions'
            }
        ),
    }
}


class PlatformManagerTest(base.TestCase):

    def setUp(self):
        super(PlatformManagerTest, self).setUp()
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures)
        api_client = sclient.Client(fake_http_client)
        self.mgr = platform.PlatformManager(api_client)

    def test_get(self):
        platform = self.mgr.get()
        self.assertIn('Platform', repr(platform))
        self.assertEqual('http://example.com/v1', platform.uri)
        self.assertEqual('platform', platform.type)
        self.assertEqual('1dae5a09ef2b4d8cbf3594b0eb4f6b94',
                         platform.project_id)
        self.assertEqual('55f41cf46df74320b9486a35f5d28a11', platform.user_id)
