# Copyright 2014 - Noorul Islam K M
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

from solumclient.builder.v1 import client as builder_client
from solumclient.builder.v1 import image
from solumclient.openstack.common.apiclient import fake_client
from solumclient.tests import base

image_fixture = {
    'uri': 'http://example.com/v1/images/i1',
    'name': 'php-web-app',
    'source_uri': 'git://example.com/project/app.git',
    'type': 'image',
    'description': 'A php web application',
    'tags': ['small'],
    'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
    'user_id': '55f41cf46df74320b9486a35f5d28a11',
}

fixtures_get = {
    '/v1/images/i1': {
        'GET': (
            {},
            image_fixture
        ),
    }
}


fixtures_create = {
    '/v1/images': {
        'POST': (
            {},
            image_fixture
        ),
    }
}


class ImageManagerTest(base.TestCase):

    def test_create(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_create)
        api_client = builder_client.Client(fake_http_client)
        mgr = image.ImageManager(api_client)
        image_obj = mgr.create()
        self.assertIn('Image', repr(image_obj))
        self.assertEqual(image_fixture['uri'], image_obj.uri)
        self.assertEqual(image_fixture['type'], image_obj.type)
        self.assertEqual(image_fixture['project_id'], image_obj.project_id)
        self.assertEqual(image_fixture['user_id'], image_obj.user_id)

    def test_get(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_get)
        api_client = builder_client.Client(fake_http_client)
        mgr = image.ImageManager(api_client)
        image_obj = mgr.get(image_id='i1')
        self.assertIn('Image', repr(image_obj))
        self.assertEqual(image_fixture['uri'], image_obj.uri)
        self.assertEqual(image_fixture['type'], image_obj.type)
        self.assertEqual(image_fixture['project_id'], image_obj.project_id)
        self.assertEqual(image_fixture['user_id'], image_obj.user_id)
