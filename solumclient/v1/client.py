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

from solumclient.openstack.common.apiclient import client
from solumclient.v1 import app
from solumclient.v1 import component
from solumclient.v1 import languagepack
from solumclient.v1 import pipeline
from solumclient.v1 import plan
from solumclient.v1 import platform
from solumclient.v1 import workflow


class Client(client.BaseClient):
    """Client for the Solum v1 API."""

    service_type = "application_deployment"

    def __init__(self, http_client, extensions=None):
        """Initialize a new client for the Solum v1 API."""
        super(Client, self).__init__(http_client, extensions)
        self.apps = app.AppManager(self)
        self.components = component.ComponentManager(self)
        self.pipelines = pipeline.PipelineManager(self)
        self.platform = platform.PlatformManager(self)
        self.plans = plan.PlanManager(self)
        self.languagepacks = languagepack.LanguagePackManager(self)
        self.workflows = workflow.WorkflowManager(self)
