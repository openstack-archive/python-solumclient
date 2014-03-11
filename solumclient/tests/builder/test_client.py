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

import mock

from solumclient.builder import client
from solumclient.common import auth
from solumclient.openstack.common.apiclient import exceptions
from solumclient.tests import base


class ClientTest(base.TestCase):

    def test_client_unsupported_version(self):
        self.assertRaises(exceptions.UnsupportedVersion,
                          client.Client, '111.11', **{})

    def test_client(self):
        with mock.patch.object(auth, 'KeystoneAuthPlugin'):
            client.Client('1', **{})
