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

import six

from solumclient.common import exc
from solumclient.openstack.common.apiclient import exceptions
from solumclient.tests import base


class FakeResponse(object):
    json_data = {}

    def __init__(self, **kwargs):
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def json(self):
        return self.json_data


class ExceptionTest(base.TestCase):

    def test_from_response_with_status_code_404(self):
        json_data = {"faultstring": "fake message",
                     "debuginfo": "fake details"}
        method = 'GET'
        status_code = 404
        url = 'http://example.com:9777/v1/assemblies/fake-id'
        ex = exc.from_response(
            FakeResponse(status_code=status_code,
                         headers={"Content-Type": "application/json"},
                         json_data=json_data),
            method,
            url
            )
        self.assertIsInstance(ex, exceptions.HttpError)
        self.assertEqual(json_data["faultstring"], ex.message)
        self.assertEqual(json_data["debuginfo"], ex.details)
        self.assertEqual(method, ex.method)
        self.assertEqual(url, ex.url)
        self.assertEqual(status_code, ex.http_status)
