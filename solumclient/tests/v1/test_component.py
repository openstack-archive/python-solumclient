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

from solumclient.openstack.common.apiclient import exceptions
from solumclient.openstack.common.apiclient import fake_client
from solumclient.tests import base
from solumclient.v1 import client as sclient
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

component_fixture = {
    'uri': 'http://example.com/v1/components/c1',
    'name': 'mysql-db',
    'type': 'component',
    'description': 'A mysql db component',
    'tags': ['database'],
    'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
    'user_id': '55f41cf46df74320b9486a35f5d28a11',
    'assembly_link': {
        'href': 'http://example.com:9777/v1/assembly/a1',
        'target_name': 'a1'},
    'service_links': [{
        'href': 'http://example.com:9777/v1/services/s1',
        'target_name': 's1'}],
    'operations_uri': 'http://example.com:9777/v1/operations/o1',
    'sensors_uri': 'http://example.com:9777/v1/sensors/o2'
}

fixtures_list = {
    '/v1/components': {
        'GET': (
            {},
            component_list
        ),
    }
}

fixtures_get = {
    '/v1/components/c1': {
        'GET': (
            {},
            component_fixture
        ),
    }
}


fixtures_create = {
    '/v1/components': {
        'POST': (
            {},
            component_fixture
        ),
    }
}

fixtures_put = {
    '/v1/components/c1': {
        'PUT': (
            {},
            component_fixture
        ),
    }
}


class ComponentManagerTest(base.TestCase):

    def test_list_all(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        self.mgr = component.ComponentManager(api_client)
        components = self.mgr.list()
        self.assertEqual(2, len(components))
        self.assertIn('Component', repr(components[0]))
        self.assertEqual('http://example.com/v1/components/c1',
                         components[0].uri)
        self.assertEqual('http://example.com/v1/components/c2',
                         components[1].uri)

    def test_create(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_create)
        api_client = sclient.Client(fake_http_client)
        mgr = component.ComponentManager(api_client)
        component_obj = mgr.create()
        self.assertIn('Component', repr(component_obj))
        self.assertEqual('http://example.com/v1/components/c1',
                         component_obj.uri)
        self.assertEqual('component',
                         component_obj.type)
        self.assertEqual('1dae5a09ef2b4d8cbf3594b0eb4f6b94',
                         component_obj.project_id)
        self.assertEqual('55f41cf46df74320b9486a35f5d28a11',
                         component_obj.user_id)

    def test_get(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_get)
        api_client = sclient.Client(fake_http_client)
        mgr = component.ComponentManager(api_client)
        component_obj = mgr.get(component_id='c1')
        self.assertIn('Component', repr(component_obj))
        self.assertEqual('http://example.com/v1/components/c1',
                         component_obj.uri)
        self.assertEqual('component',
                         component_obj.type)
        self.assertEqual('1dae5a09ef2b4d8cbf3594b0eb4f6b94',
                         component_obj.project_id)
        self.assertEqual('55f41cf46df74320b9486a35f5d28a11',
                         component_obj.user_id)

    def test_put(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_put)
        api_client = sclient.Client(fake_http_client)
        mgr = component.ComponentManager(api_client)
        component_obj = mgr.put(component_id='c1')
        self.assertIn('Component', repr(component_obj))
        self.assertEqual('http://example.com/v1/components/c1',
                         component_obj.uri)
        self.assertEqual('component',
                         component_obj.type)
        self.assertEqual('1dae5a09ef2b4d8cbf3594b0eb4f6b94',
                         component_obj.project_id)
        self.assertEqual('55f41cf46df74320b9486a35f5d28a11',
                         component_obj.user_id)

    def test_find_one(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = component.ComponentManager(api_client)
        components = mgr.findall(name='php-web-app')
        self.assertEqual(1, len(components))
        self.assertIn('Component', repr(components[0]))
        self.assertEqual(component_list[0]['uri'], components[0].uri)

    def test_find_one_only(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = component.ComponentManager(api_client)
        result = mgr.find(name_or_id='php-web-app')
        self.assertEqual(component_list[0]['uri'], result.uri)

    def test_find_none(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = component.ComponentManager(api_client)
        self.assertRaises(exceptions.NotFound, mgr.find, name_or_id='test')
