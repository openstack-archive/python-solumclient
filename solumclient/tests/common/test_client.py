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

import mock
import requests

from solumclient.common import client
from solumclient.openstack.common.apiclient import auth
from solumclient.openstack.common.apiclient import client as api_client
from solumclient.openstack.common.apiclient import exceptions
from solumclient.tests import base


class TestClient(api_client.BaseClient):
    service_type = "test"


class FakeAuthPlugin(auth.BaseAuthPlugin):
    auth_system = "fake"
    attempt = -1

    def _do_authenticate(self, http_client):
        pass

    def token_and_endpoint(self, endpoint_type, service_type):
        self.attempt = self.attempt + 1
        return ("token-%s" % self.attempt, "/endpoint-%s" % self.attempt)


class ClientTest(base.TestCase):
    def test_client_request(self):
        http_client = client.HTTPClient(FakeAuthPlugin())
        mock_request = mock.Mock()
        mock_request.return_value = requests.Response()
        mock_request.return_value.status_code = 200
        with mock.patch("requests.Session.request", mock_request):
            http_client.client_request(
                TestClient(http_client), "GET", "/resource", json={"1": "2"})
            requests.Session.request.assert_called_with(
                "GET",
                "/endpoint-0/resource",
                headers={
                    "User-Agent": http_client.user_agent,
                    "Content-Type": "application/json",
                    "X-Auth-Token": "token-0",
                    "X-Password": "",
                    "X-User-ID": "",
                    "X-Project": ""
                },
                data='{"1": "2"}',
                verify=True)

    def test_client_with_response_404_status_code(self):
        http_client = client.HTTPClient(FakeAuthPlugin())
        mock_request = mock.Mock()
        mock_request.return_value = requests.Response()
        mock_request.return_value.status_code = 404
        with mock.patch("requests.Session.request", mock_request):
            self.assertRaises(
                exceptions.HttpError, http_client.client_request,
                TestClient(http_client), "GET", "/resource")

    def test_client_with_invalid_endpoint(self):
        http_client = client.HTTPClient(FakeAuthPlugin())
        mock_request = mock.Mock()
        mock_request.side_effect = requests.ConnectionError
        with mock.patch("requests.Session.request", mock_request):
            self.assertRaises(
                requests.ConnectionError, http_client.client_request,
                TestClient(http_client), "GET", "/resource")

    def test_client_with_invalid_service_catalog(self):
        http_client = client.HTTPClient(FakeAuthPlugin())
        mock_request = mock.Mock()
        mock_request.side_effect = exceptions.EndpointException
        with mock.patch("requests.Session.request", mock_request):
            self.assertRaises(
                exceptions.EndpointException, http_client.client_request,
                TestClient(http_client), "GET", "/resource")

    def test_client_with_connection_refused(self):
        http_client = client.HTTPClient(FakeAuthPlugin())
        mock_request = mock.Mock()
        mock_request.side_effect = exceptions.ConnectionRefused
        with mock.patch("requests.Session.request", mock_request):
            self.assertRaises(
                exceptions.ConnectionRefused, http_client.client_request,
                TestClient(http_client), "GET", "/resource")
