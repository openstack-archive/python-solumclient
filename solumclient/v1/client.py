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

from solumclient import client as solum_client
from solumclient.v1 import app
from solumclient.v1 import component
from solumclient.v1 import languagepack
from solumclient.v1 import pipeline
from solumclient.v1 import plan
from solumclient.v1 import platform
from solumclient.v1 import workflow


class Client(object):
    """Client for the Solum v1 API."""

    service_type = "application_deployment"

    def __init__(self, *args, **kwargs):
        """Initialize a new client for the Solum v1 API."""
        if not kwargs.get('auth_plugin'):
            kwargs['auth_plugin'] = solum_client.get_auth_plugin(**kwargs)
        self.auth_plugin = kwargs.get('auth_plugin')

        self.http_client = solum_client.construct_http_client(**kwargs)
        self.apps = app.AppManager(self.http_client)
        self.components = component.ComponentManager(self.http_client)
        self.pipelines = pipeline.PipelineManager(self.http_client)
        self.platform = platform.PlatformManager(self.http_client)
        self.plans = plan.PlanManager(self.http_client)
        self.languagepacks = languagepack.LanguagePackManager(self.http_client)
        self.workflows = workflow.WorkflowManager(self.http_client)
