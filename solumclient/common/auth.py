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

from keystoneclient.auth.identity import v2 as v2_auth
from keystoneclient.auth.identity import v3 as v3_auth
from keystoneclient import discover
from keystoneclient import exceptions as ks_exc
from keystoneclient import session
from oslo_utils import strutils
import six.moves.urllib.parse as urlparse

from solumclient.common.apiclient import auth
from solumclient.common.apiclient import exceptions
from solumclient.common import exc


def _discover_auth_versions(session, auth_url):
    # discover the API versions the server is supporting based on the
    # given URL
    v2_auth_url = None
    v3_auth_url = None
    try:
        ks_discover = discover.Discover(session=session, auth_url=auth_url)
        v2_auth_url = ks_discover.url_for('2.0')
        v3_auth_url = ks_discover.url_for('3.0')
    except ks_exc.DiscoveryFailure:
        raise
    except exceptions.ClientException:
        # Identity service may not support discovery. In that case,
        # try to determine version from auth_url
        url_parts = urlparse.urlparse(auth_url)
        (scheme, netloc, path, params, query, fragment) = url_parts
        path = path.lower()
        if path.startswith('/v3'):
            v3_auth_url = auth_url
        elif path.startswith('/v2'):
            v2_auth_url = auth_url
        else:
            raise exc.CommandError('Unable to determine the Keystone '
                                   'version to authenticate with '
                                   'using the given auth_url.')
    return v2_auth_url, v3_auth_url


def _get_keystone_session(**kwargs):
    # TODO(fabgia): the heavy lifting here should be really done by Keystone.
    # Unfortunately Keystone does not support a richer method to perform
    # discovery and return a single viable URL. A bug against Keystone has
    # been filed: https://bugs.launchpad.net/python-keystoneclient/+bug/1330677

    # first create a Keystone session
    cacert = kwargs.pop('cacert', None)
    cert = kwargs.pop('cert', None)
    key = kwargs.pop('key', None)
    insecure = kwargs.pop('insecure', False)
    auth_url = kwargs.pop('auth_url', None)
    project_id = kwargs.pop('project_id', None)
    project_name = kwargs.pop('project_name', None)

    if insecure:
        verify = False
    else:
        verify = cacert or True

    if cert and key:
        # passing cert and key together is deprecated in favour of the
        # requests lib form of having the cert and key as a tuple
        cert = (cert, key)

    # create the keystone client session
    ks_session = session.Session(verify=verify, cert=cert)
    v2_auth_url, v3_auth_url = _discover_auth_versions(ks_session, auth_url)

    username = kwargs.pop('username', None)
    user_id = kwargs.pop('user_id', None)
    user_domain_name = kwargs.pop('user_domain_name', None)
    user_domain_id = kwargs.pop('user_domain_id', None)
    project_domain_name = kwargs.pop('project_domain_name', None)
    project_domain_id = kwargs.pop('project_domain_id', None)
    auth = None

    use_domain = (user_domain_id or user_domain_name or
                  project_domain_id or project_domain_name)
    use_v3 = v3_auth_url and (use_domain or (not v2_auth_url))
    use_v2 = v2_auth_url and not use_domain

    if use_v3:
        # the auth_url as v3 specified
        # e.g. http://no.where:5000/v3
        # Keystone will return only v3 as viable option
        auth = v3_auth.Password(
            v3_auth_url,
            username=username,
            password=kwargs.pop('password', None),
            user_id=user_id,
            user_domain_name=user_domain_name,
            user_domain_id=user_domain_id,
            project_name=project_name,
            project_id=project_id,
            project_domain_name=project_domain_name,
            project_domain_id=project_domain_id)
    elif use_v2:
        # the auth_url as v2 specified
        # e.g. http://no.where:5000/v2.0
        # Keystone will return only v2 as viable option
        auth = v2_auth.Password(
            v2_auth_url,
            username,
            kwargs.pop('password', None),
            tenant_id=project_id,
            tenant_name=project_name)
    else:
        raise exc.CommandError('Unable to determine the Keystone version '
                               'to authenticate with using the given '
                               'auth_url.')

    ks_session.auth = auth
    return ks_session


def _get_endpoint(ks_session, **kwargs):
    """Get an endpoint using the provided keystone session."""

    # set service specific endpoint types
    endpoint_type = kwargs.get('endpoint_type') or 'publicURL'
    service_type = kwargs.get('service_type') or 'application_deployment'

    endpoint = ks_session.get_endpoint(service_type=service_type,
                                       interface=endpoint_type,
                                       region_name=kwargs.get('region_name'))

    return endpoint


class KeystoneAuthPlugin(auth.BaseAuthPlugin):

    opt_names = ['tenant_id', 'region_name', 'auth_token',
                 'service_type', 'endpoint_type', 'cacert',
                 'auth_url', 'insecure', 'cert_file', 'key_file',
                 'cert', 'key', 'tenant_name', 'project_name',
                 'project_id', 'project_domain_id', 'project_domain_name',
                 'user_id', 'user_domain_id', 'user_domain_name',
                 'password', 'username', 'endpoint']

    def __init__(self, auth_system=None, **kwargs):
        self.opt_names.extend(self.common_opt_names)
        super(KeystoneAuthPlugin, self).__init__(auth_system, **kwargs)

    def _do_authenticate(self, http_client):
        token = self.opts.get('token') or self.opts.get('auth_token')
        endpoint = self.opts.get('endpoint')
        if not (token and endpoint):
            project_id = (self.opts.get('project_id') or
                          self.opts.get('tenant_id'))
            project_name = (self.opts.get('project_name') or
                            self.opts.get('tenant_name'))
            ks_kwargs = {
                'username': self.opts.get('username'),
                'password': self.opts.get('password'),
                'user_id': self.opts.get('user_id'),
                'user_domain_id': self.opts.get('user_domain_id'),
                'user_domain_name': self.opts.get('user_domain_name'),
                'project_id': project_id,
                'project_name': project_name,
                'project_domain_name': self.opts.get('project_domain_name'),
                'project_domain_id': self.opts.get('project_domain_id'),
                'auth_url': self.opts.get('auth_url'),
                'cacert': self.opts.get('cacert'),
                'cert': self.opts.get('cert'),
                'key': self.opts.get('key'),
                'insecure': strutils.bool_from_string(
                    self.opts.get('insecure')),
                'endpoint_type': self.opts.get('endpoint_type'),
            }

            # retrieve session
            ks_session = _get_keystone_session(**ks_kwargs)
            token = ks_session.get_token()
            endpoint = (self.opts.get('endpoint') or
                        _get_endpoint(ks_session, **ks_kwargs))
        self.opts['token'] = token
        self.opts['endpoint'] = endpoint

    def token_and_endpoint(self, endpoint_type, service_type):
        token = self.opts.get('token')
        if callable(token):
            token = token()
        return token, self.opts.get('endpoint')

    def sufficient_options(self):
        """Check if all required options are present.

        :raises: AuthPluginOptionsMissing
        """
        has_token = self.opts.get('token') or self.opts.get('auth_token')
        no_auth = has_token and self.opts.get('endpoint')
        has_project = (self.opts.get('project_id')
                       or (self.opts.get('project_name')
                           and (self.opts.get('user_domain_name')
                           or self.opts.get('user_domain_id'))))
        has_tenant = self.opts.get('tenant_id') or self.opts.get('tenant_name')
        has_credential = (self.opts.get('username')
                          and (has_project or has_tenant)
                          and self.opts.get('password')
                          and self.opts.get('auth_url'))
        missing = not (no_auth or has_credential)
        if missing:
            missing_opts = []
            opts = ['token', 'endpoint', 'username', 'password', 'auth_url',
                    'tenant_id', 'tenant_name']
            for opt in opts:
                if not self.opts.get(opt):
                    missing_opts.append(opt)
            raise exceptions.AuthPluginOptionsMissing(missing_opts)
