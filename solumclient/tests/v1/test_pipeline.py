# Copyright 2014 - Rackspace Hosting
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
from solumclient.v1 import pipeline

pipeline_list = [
    {
        'uri': 'http://example.com/v1/pipelines/x1',
        'name': 'database',
        'type': 'pipeline',
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
        'uri': 'http://example.com/v1/pipelines/x2',
        'name': 'load_balancer',
        'type': 'pipeline',
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

pipeline_fixture = {
    'uri': 'http://example.com/v1/pipelines/x1',
    'name': 'database',
    'type': 'pipeline',
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
    '/v1/pipelines': {
        'GET': (
            {},
            pipeline_list
        ),
    }
}


fixtures_get = {
    '/v1/pipelines/x1': {
        'GET': (
            {},
            pipeline_fixture
        ),
    }
}


fixtures_create = {
    '/v1/pipelines': {
        'POST': (
            {},
            pipeline_fixture
        ),
    }
}

fixtures_put = {
    '/v1/pipelines/x1': {
        'PUT': (
            {},
            pipeline_fixture
        ),
    }
}

fixtures_delete = {
    '/v1/pipelines/x1': {
        'DELETE': (
            {},
            {},
        ),
    }
}


class PipelineManagerTest(base.TestCase):

    def assert_pipeline_object(self, pipeline_obj):
        self.assertIn('Pipeline', repr(pipeline_obj))
        self.assertEqual(pipeline_fixture['uri'], pipeline_obj.uri)
        self.assertEqual(pipeline_fixture['type'], pipeline_obj.type)
        self.assertEqual(pipeline_fixture['project_id'],
                         pipeline_obj.project_id)
        self.assertEqual(pipeline_fixture['user_id'], pipeline_obj.user_id)

    def test_list_all(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        pipelines = mgr.list()
        self.assertEqual(2, len(pipelines))
        self.assertIn('Pipeline', repr(pipelines[0]))
        self.assertEqual(pipeline_list[0]['uri'], pipelines[0].uri)
        self.assertEqual(pipeline_list[1]['uri'], pipelines[1].uri)

    def test_find_one(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        pipelines = mgr.findall(name='database')
        self.assertEqual(1, len(pipelines))
        self.assertIn('Pipeline', repr(pipelines[0]))
        self.assertEqual(pipeline_list[0]['uri'], pipelines[0].uri)

    def test_find_one_only(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        result = mgr.find(name_or_id='database')
        self.assertEqual(pipeline_list[0]['uri'], result.uri)

    def test_find_none(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        self.assertRaises(exceptions.NotFound, mgr.find, name_or_id='what')

    def test_create(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_create)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        pipeline_obj = mgr.create()
        self.assert_pipeline_object(pipeline_obj)

    def test_get(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_get)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        pipeline_obj = mgr.get(pipeline_id='x1')
        self.assert_pipeline_object(pipeline_obj)

    def test_put(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_put)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        pipeline_obj = mgr.put(pipeline_id='x1')
        self.assert_pipeline_object(pipeline_obj)

    def test_delete(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_delete)
        api_client = sclient.Client(fake_http_client)
        mgr = pipeline.PipelineManager(api_client)
        mgr.delete(pipeline_id='x1')
        fake_http_client.assert_called('DELETE', '/v1/pipelines/x1')
