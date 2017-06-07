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

import contextlib
import time

from keystoneclient import adapter
from oslo_utils import strutils

from solumclient.common.apiclient import client as api_client
from solumclient.common import auth
from solumclient.common import exc

API_NAME = 'solum'
VERSION_MAP = {
    '1': 'solumclient.v1.client.Client',
}


def Client(version, *args, **kwargs):
    client_class = api_client.BaseClient.get_class(API_NAME, version,
                                                   VERSION_MAP)
    kwargs['token'] = kwargs.get('token') or kwargs.get('auth_token')
    return client_class(version, *args, **kwargs)


def _adjust_params(kwargs):
    timeout = kwargs.get('timeout')
    if timeout is not None:
        timeout = int(timeout)
        if timeout <= 0:
            timeout = None

    insecure = strutils.bool_from_string(kwargs.get('insecure'))
    verify = kwargs.get('verify')
    if verify is None:
        if insecure:
            verify = False
        else:
            verify = kwargs.get('cacert') or True

    cert = kwargs.get('cert_file')
    key = kwargs.get('key_file')
    if cert and key:
        cert = cert, key
    return {'verify': verify, 'cert': cert, 'timeout': timeout}


def get_client(version, **kwargs):
    """Get an authenticated client, based on the credentials in the kwargs.

    :param api_version: the API version to use ('1')
    :param kwargs: keyword args containing credentials, either:

            * session: a keystoneauth/keystoneclient session object
            * service_type: The default service_type for URL discovery
            * service_name: The default service_name for URL discovery
            * interface: The default interface for URL discovery
                         (Default: public)
            * region_name: The default region_name for URL discovery
            * endpoint_override: Always use this endpoint URL for requests
                                 for this solumclient
            * auth: An auth plugin to use instead of the session one
            * user_agent: The User-Agent string to set
                          (Default is python-solumclient)
            * connect_retries: the maximum number of retries that should be
                               attempted for connection errors
            * logger: A logging object

            or (DEPRECATED):

            * os_token: pre-existing token to re-use
            * os_endpoint: Solum API endpoint

            or (DEPRECATED):

            * os_username: name of user
            * os_password: user's password
            * os_user_id: user's id
            * os_user_domain_id: the domain id of the user
            * os_user_domain_name: the domain name of the user
            * os_project_id: the user project id
            * os_tenant_id: V2 alternative to os_project_id
            * os_project_name: the user project name
            * os_tenant_name: V2 alternative to os_project_name
            * os_project_domain_name: domain name for the user project
            * os_project_domain_id: domain id for the user project
            * os_auth_url: endpoint to authenticate against
            * os_cert|os_cacert: path of CA TLS certificate
            * os_key: SSL private key
            * insecure: allow insecure SSL (no cert verification)
    """
    endpoint = kwargs.get('os_endpoint')

    cli_kwargs = {
        'username': kwargs.get('os_username'),
        'password': kwargs.get('os_password'),
        'tenant_id': (kwargs.get('os_tenant_id')
                      or kwargs.get('os_project_id')),
        'tenant_name': (kwargs.get('os_tenant_name')
                        or kwargs.get('os_project_name')),
        'auth_url': kwargs.get('os_auth_url'),
        'region_name': kwargs.get('os_region_name'),
        'service_type': kwargs.get('os_service_type'),
        'endpoint_type': kwargs.get('os_endpoint_type'),
        'cacert': kwargs.get('os_cacert'),
        'cert_file': kwargs.get('os_cert'),
        'key_file': kwargs.get('os_key'),
        'token': kwargs.get('os_token') or kwargs.get('os_auth_token'),
        'user_domain_name': kwargs.get('os_user_domain_name'),
        'user_domain_id': kwargs.get('os_user_domain_id'),
        'project_domain_name': kwargs.get('os_project_domain_name'),
        'project_domain_id': kwargs.get('os_project_domain_id'),
    }

    cli_kwargs.update(kwargs)
    cli_kwargs.update(_adjust_params(cli_kwargs))

    return Client(version, endpoint, **cli_kwargs)


def get_auth_plugin(**kwargs):
    auth_plugin = auth.KeystoneAuthPlugin(
        auth_url=kwargs.get('auth_url'),
        service_type=kwargs.get('service_type'),
        token=kwargs.get('token'),
        endpoint_type=kwargs.get('endpoint_type'),
        endpoint=kwargs.get('endpoint'),
        cacert=kwargs.get('cacert'),
        tenant_id=kwargs.get('project_id') or kwargs.get('tenant_id'),
        username=kwargs.get('username'),
        password=kwargs.get('password'),
        tenant_name=kwargs.get('tenant_name') or kwargs.get('project_name'),
        user_domain_name=kwargs.get('user_domain_name'),
        user_domain_id=kwargs.get('user_domain_id'),
        project_domain_name=kwargs.get('project_domain_name'),
        project_domain_id=kwargs.get('project_domain_id')
    )
    return auth_plugin


LEGACY_OPTS = ('auth_plugin', 'auth_url', 'token', 'insecure', 'cacert',
               'tenant_id', 'project_id', 'username', 'password',
               'project_name', 'tenant_name',
               'user_domain_name', 'user_domain_id',
               'project_domain_name', 'project_domain_id',
               'key_file', 'cert_file', 'verify', 'timeout', 'cert')


def construct_http_client(**kwargs):
    kwargs = kwargs.copy()
    if kwargs.get('session') is not None:
        # Drop legacy options
        for opt in LEGACY_OPTS:
            kwargs.pop(opt, None)

        service_type_get = kwargs.pop('service_type',
                                      'application_deployment')

        return SessionClient(
            session=kwargs.pop('session'),
            service_type=service_type_get or 'application_deployment',
            interface=kwargs.pop('interface', kwargs.pop('endpoint_type',
                                                         'publicURL')),
            region_name=kwargs.pop('region_name', None),
            user_agent=kwargs.pop('user_agent', 'python-solumclient'),
            auth=kwargs.get('auth', None),
            timings=kwargs.pop('timings', None),
            **kwargs)
    else:
        return api_client.BaseClient(api_client.HTTPClient(
            auth_plugin=kwargs.get('auth_plugin'),
            region_name=kwargs.get('region_name'),
            endpoint_type=kwargs.get('endpoint_type'),
            original_ip=kwargs.get('original_ip'),
            verify=kwargs.get('verify'),
            cert=kwargs.get('cert'),
            timeout=kwargs.get('timeout'),
            timings=kwargs.get('timings'),
            keyring_saver=kwargs.get('keyring_saver'),
            debug=kwargs.get('debug'),
            user_agent=kwargs.get('user_agent'),
            http=kwargs.get('http')
        ))


@contextlib.contextmanager
def record_time(times, enabled, *args):
    """Record the time of a specific action.

    :param times: A list of tuples holds time data.
    :type times: list
    :param enabled: Whether timing is enabled.
    :type enabled: bool
    :param args: Other data to be stored besides time data, these args
                 will be joined to a string.
    """
    if not enabled:
        yield
    else:
        start = time.time()
        yield
        end = time.time()
        times.append((' '.join(args), start, end))


class SessionClient(adapter.LegacyJsonAdapter):
    def __init__(self, *args, **kwargs):
        self.times = []
        self.timings = kwargs.pop('timings', False)
        super(SessionClient, self).__init__(*args, **kwargs)

    def request(self, url, method, **kwargs):
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        raise_exc = kwargs.pop('raise_exc', True)
        with record_time(self.times, self.timings, method, url):
            resp, body = super(SessionClient, self).request(url,
                                                            method,
                                                            raise_exc=False,
                                                            **kwargs)

        if raise_exc and resp.status_code >= 400:
            raise exc.from_response(resp, body)
        return resp
