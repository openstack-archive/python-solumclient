# Copyright 2014 - Rackspace
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

from solumclient.builder.v1 import image
from solumclient.openstack.common.apiclient import fake_client
from solumclient.tests import base
from solumclient.v1 import client as sclient
from solumclient.v1 import languagepack

languagepack_list = [
    {
        'uri': 'http://example.com/v1/language_packs/x1',
        'name': 'database',
        'language_pack_type': 'python',
        'description': 'Python Language pack',
        'tags': ['python'],
        'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
        'user_id': '55f41cf46df74320b9486a35f5d28a11',
        'language_implementation': 'python',
        'compiler_versions': '2.6',
        'os_platform': 'ubuntu 12.04',
        'attr_blob': '',
        'service_id': 1
    },
    {
        'uri': 'http://example.com/v1/language_packs/x2',
        'name': 'database',
        'language_pack_type': 'java',
        'description': 'Java Language pack',
        'tags': ['java'],
        'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
        'user_id': '55f41cf46df74320b9486a35f5d28a11',
        'language_implementation': 'java',
        'compiler_versions': '7.0',
        'os_platform': 'ubuntu 12.04',
        'attr_blob': '',
        'service_id': 1
    }
]

languagepack_fixture = {
    'uri': 'http://example.com/v1/language_packs/x1',
    'name': 'database',
    'language_pack_type': 'java',
    'description': 'Java Language pack',
    'tags': ['java'],
    'project_id': '1dae5a09ef2b4d8cbf3594b0eb4f6b94',
    'user_id': '55f41cf46df74320b9486a35f5d28a11',
    'language_implementation': 'java',
    'compiler_versions': '7.0',
    'os_platform': 'ubuntu 12.04',
    'attr_blob': '',
    'service_id': 1
}

fixtures_list = {
    '/v1/language_packs': {
        'GET': (
            {},
            languagepack_list
        ),
    }
}


fixtures_get = {
    '/v1/language_packs/x1': {
        'GET': (
            {},
            languagepack_fixture
        ),
    }
}


fixtures_create = {
    '/v1/language_packs': {
        'POST': (
            {},
            languagepack_fixture
        ),
    }
}

image_fixture = {
    'name': 'lp1',
    'source_uri': 'github.com/test',
    'lp_metadata': 'sample_lp_metadata'
}

fixtures_build = {
    '/v1/images': {
        'POST': (
            {},
            image_fixture
        ),
    }
}


class LanguagePackManagerTest(base.TestCase):

    def assert_lp_object(self, lp_obj):
        self.assertIn('LanguagePack', repr(lp_obj))
        self.assertEqual(languagepack_fixture['uri'], lp_obj.uri)
        self.assertEqual(languagepack_fixture['language_pack_type'],
                         lp_obj.language_pack_type)
        self.assertEqual(languagepack_fixture['project_id'], lp_obj.project_id)
        self.assertEqual(languagepack_fixture['user_id'], lp_obj.user_id)

    def test_list_all(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_list)
        api_client = sclient.Client(fake_http_client)
        mgr = languagepack.LanguagePackManager(api_client)
        languagepacks = mgr.list()
        self.assertEqual(2, len(languagepacks))
        self.assertIn('LanguagePack', repr(languagepacks[0]))
        self.assertEqual(languagepack_list[0]['uri'],
                         languagepacks[0].uri)
        self.assertEqual(languagepack_list[1]['uri'],
                         languagepacks[1].uri)

    def test_create(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_create)
        api_client = sclient.Client(fake_http_client)
        mgr = languagepack.LanguagePackManager(api_client)
        languagepack_obj = mgr.create()
        self.assert_lp_object(languagepack_obj)

    def test_get(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_get)
        api_client = sclient.Client(fake_http_client)
        mgr = languagepack.LanguagePackManager(api_client)
        languagepack_obj = mgr.get(lp_id='x1')
        self.assert_lp_object(languagepack_obj)

    def test_build(self):
        fake_http_client = fake_client.FakeHTTPClient(fixtures=fixtures_build)
        api_client = sclient.Client(fake_http_client)
        mgr = image.ImageManager(api_client)
        image_obj = mgr.create(name='lp1',
                               source_uri='github.com/test',
                               lp_metadata='sample_lp_metadata')
        self.assert_image_object(image_obj)

    def assert_image_object(self, image_obj):
        self.assertIn('Image', repr(image_obj))
        self.assertEqual(image_fixture['source_uri'], image_obj.source_uri)
        self.assertEqual(image_fixture['name'], image_obj.name)
        self.assertEqual(image_fixture['lp_metadata'], image_obj.lp_metadata)
