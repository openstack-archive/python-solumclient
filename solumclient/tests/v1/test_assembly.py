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
from solumclient.v1 import assembly
from solumclient.v1 import client as solumclient

assembly_list = [
    {
        'uri': 'http://example.com/v1/assemblies/x1',
        'name': 'database',
        'type': 'assembly',
        'description': 'A mysql database',
        'tags': ['small'],
        'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
        'user_id': '55f41cf46df74320b9486a35f5d28a11',
        'component_links': [{
            'href': 'http://example.com:9777/v1/components/x1',
            'target_name': 'x1'}],
        'operations_uri': 'http://example.com:9777/v1/operations/o1',
        'sensors_uri': 'http://example.com:9777/v1/sensors/s1'
    },
    {
        'uri': 'http://example.com/v1/assemblies/x2',
        'name': 'load_balancer',
        'type': 'assembly',
        'description': 'A load balancer',
        'tags': ['small'],
        'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
        'user_id': '55f41cf46df74320b9486a35f5d28a11',
        'component_links': [{
            'href': 'http://example.com:9777/v1/components/x2',
            'target_name': 'x2'}],
        'operations_uri': 'http://example.com:9777/v1/operations/o2',
        'sensors_uri': 'http://example.com:9777/v1/sensors/s2'
    }
]

fixtures = {
    '/v1/assemblies': {
        'GET': (
            {},
            assembly_list
        ),
    }
}


class AssemblyManagerTest(base.TestCase):

    def setUp(self):
        super(AssemblyManagerTest, self).setUp()
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures)
        api_client = solumclient.Client(fake_http_client)
        self.mgr = assembly.AssemblyManager(api_client)

    def test_list_all(self):
        assemblies = self.mgr.list()
        self.assertEqual(len(assemblies), 2)
        self.assertIn('Assembly', repr(assemblies[0]))
        self.assertEqual(assemblies[0].uri,
                         'http://example.com/v1/assemblies/x1')
        self.assertEqual(assemblies[1].uri,
                         'http://example.com/v1/assemblies/x2')
