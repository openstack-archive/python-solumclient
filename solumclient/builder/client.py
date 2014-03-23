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

from solumclient.common import auth
from solumclient.common import client
from solumclient.openstack.common.apiclient import client as api_client

API_NAME = 'builder'
VERSION_MAP = {
    '1': 'solumclient.builder.v1.client.Client',
}


def Client(version, **kwargs):
    client_class = api_client.BaseClient.get_class(API_NAME, version,
                                                   VERSION_MAP)
    keystone_auth = auth.KeystoneAuthPlugin(
        username=kwargs.get('username'),
        password=kwargs.get('password'),
        tenant_name=kwargs.get('tenant_name'),
        token=kwargs.get('token'),
        auth_url=kwargs.get('auth_url'),
        endpoint=kwargs.get('endpoint'))
    http_client = client.HTTPClient(keystone_auth)
    return client_class(http_client)
