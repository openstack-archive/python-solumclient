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
from solumclient.v1 import assembly
from solumclient.v1 import client as sclient

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

assembly_fixture = {
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
}

fixtures_list = {
    '/v1/assemblies': {
        'GET': (
            {},
            assembly_list
        ),
    }
}


fixtures_get = {
    '/v1/assemblies/x1': {
        'GET': (
            {},
            assembly_fixture
        ),
    }
}


fixtures_create = {
    '/v1/assemblies': {
        'POST': (
            {},
            assembly_fixture
        ),
    }
}

fixtures_put = {
    '/v1/assemblies/x1': {
        'PUT': (
            {},
            assembly_fixture
        ),
    }
}


class AssemblyManagerTest(base.TestCase):

    def assert_assembly_object(self, assembly_obj):
        self.assertIn('Assembly', repr(assembly_obj))
        self.assertEqual(assembly_fixture['uri'], assembly_obj.uri)
        self.assertEqual(assembly_fixture['type'], assembly_obj.type)
        self.assertEqual(assembly_fixture['project_id'],
                         assembly_obj.project_id)
        self.assertEqual(assembly_fixture['user_id'], assembly_obj.user_id)

    def test_list_all(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        assemblies = mgr.list()
        self.assertEqual(len(assemblies), 2)
        self.assertIn('Assembly', repr(assemblies[0]))
        self.assertEqual(assembly_list[0]['uri'], assemblies[0].uri)
        self.assertEqual(assembly_list[1]['uri'], assemblies[1].uri)

    def test_find_one(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        assemblies = mgr.findall(name='database')
        self.assertEqual(len(assemblies), 1)
        self.assertIn('Assembly', repr(assemblies[0]))
        self.assertEqual(assembly_list[0]['uri'], assemblies[0].uri)

    def test_find_one_only(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        result = mgr.find(name_or_id='database')
        self.assertEqual(assembly_list[0]['uri'], result.uri)

    def test_find_none(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        self.assertRaises(exceptions.NotFound, mgr.find, name_or_id='what')

    def test_create(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_create)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        assembly_obj = mgr.create()
        self.assert_assembly_object(assembly_obj)

    def test_get(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_get)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        assembly_obj = mgr.get(assembly_id='x1')
        self.assert_assembly_object(assembly_obj)

    def test_put(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_put)
        api_client = sclient.Client(fake_http_client)
        mgr = assembly.AssemblyManager(api_client)
        assembly_obj = mgr.put(assembly_id='x1')
        self.assert_assembly_object(assembly_obj)
