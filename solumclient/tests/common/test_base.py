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

from solumclient.openstack.common.apiclient import base
from solumclient.openstack.common.apiclient import client
from solumclient.openstack.common.apiclient import fake_client
from solumclient.tests import base as test_base


fixture1 = {
    '/foo_resource': {
        'GET': (
            {},
            {'id': 1, 'name': 'foo'}
        ),
    }
}

fixture2 = {
    '/foo_resource': {
        'GET': (
            {},
            {'foo_resource': {'id': 1, 'name': 'foo'}}
        ),
    }
}

fixture3 = {
    '/foo_resources': {
        'GET': (
            {},
            [
                {'id': 1, 'name': 'foo'},
                {'id': 2, 'name': 'bar'}
            ]
        ),
    }
}

fixture4 = {
    '/foo_resources': {
        'GET': (
            {},
            {'foo_resources': [
                {'id': 1, 'name': 'foo'},
                {'id': 2, 'name': 'bar'}
            ]}
        ),
    }
}


class FooResource(base.Resource):
    pass


class FooResourceManager(base.BaseManager):
    resource_class = FooResource

    def get(self):
        return self._get("/foo_resource")

    def get_with_response_key(self):
        return self._get("/foo_resource", "foo_resource")

    def list(self):
        return self._list("/foo_resources")

    def list_with_response_key(self):
        return self._list("/foo_resources", "foo_resources")


class TestClient(client.BaseClient):

    service_type = "test"

    def __init__(self, http_client, extensions=None):
        super(TestClient, self).__init__(
            http_client, extensions=extensions)

        self.foo_resource = FooResourceManager(self)


class BaseManagerTest(test_base.TestCase):

    def test_get(self):
        http_client = fake_client.FakeHTTPClient(fixtures=fixture1)
        tc = TestClient(http_client)
        tc.foo_resource.get()

    def test_get_with_response_key(self):
        http_client = fake_client.FakeHTTPClient(fixtures=fixture2)
        tc = TestClient(http_client)
        tc.foo_resource.get_with_response_key()

    def test_list(self):
        http_client = fake_client.FakeHTTPClient(fixtures=fixture3)
        tc = TestClient(http_client)
        tc.foo_resource.list()

    def test_list_with_response_key(self):
        http_client = fake_client.FakeHTTPClient(fixtures=fixture4)
        tc = TestClient(http_client)
        tc.foo_resource.list_with_response_key()
