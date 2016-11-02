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

from solumclient.builder.v1 import image
from solumclient.common.apiclient import client


class Client(client.BaseClient):
    """Client for the Solum v1 API."""

    service_type = "image_builder"

    def __init__(self, http_client, extensions=None):
        """Initialize a new client for the Builder v1 API."""
        super(Client, self).__init__(http_client, extensions)
        self.images = image.ImageManager(self)
