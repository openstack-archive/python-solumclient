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
from solumclient.v1 import client as solumclient
from solumclient.v1 import component


component_list = [
    {
        'uri': 'http://example.com/v1/components/c1',
        'name': 'php-web-app',
        'type': 'component',
        'description': 'A php web application component',
        'tags': ['web_app'],
        'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
        'user_id': '55f41cf46df74320b9486a35f5d28a11',
        'assembly_link': {
            ' href': 'http://example.com:9777/v1/assembly/a1',
            'target_name': 'a1'},
        'service_links': [{
            'href': 'http://example.com:9777/v1/services/s1',
            'target_name': 's1'}],
        'operations_uri': 'http://example.com:9777/v1/operations/o1',
        'sensors_uri': 'http://example.com:9777/v1/sensors/s1'
    },
    {
        'uri': 'http://example.com/v1/components/c2',
        'name': 'mysql-db',
        'type': 'component',
        'description': 'A mysql db component',
        'tags': ['database'],
        'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
        'user_id': '55f41cf46df74320b9486a35f5d28a11',
        'assembly_link': {
            'href': 'http://example.com:9777/v1/assembly/a2',
            'target_name': 'a2'},
        'service_links': [{
            'href': 'http://example.com:9777/v1/services/s2',
            'target_name': 's2'}],
        'operations_uri': 'http://example.com:9777/v1/operations/o2',
        'sensors_uri': 'http://example.com:9777/v1/sensors/s2'
    }
]

fixtures = {
    '/v1/components': {
        'GET': (
            {},
            component_list
        ),
    }
}


class ComponentManagerTest(base.TestCase):

    def setUp(self):
        super(ComponentManagerTest, self).setUp()
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures)
        api_client = solumclient.Client(fake_http_client)
        self.mgr = component.ComponentManager(api_client)

    def test_list_all(self):
        components = self.mgr.list()
        self.assertEqual(len(components), 2)
        self.assertIn('Component', repr(components[0]))
        self.assertEqual(components[0].uri,
                         'http://example.com/v1/components/c1')
        self.assertEqual(components[1].uri,
                         'http://example.com/v1/components/c2')
