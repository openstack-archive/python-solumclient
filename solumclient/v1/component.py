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

from solumclient.common import base as solum_base
from solumclient.common import exc
from solumclient.openstack.common.apiclient import base as apiclient_base
from solumclient.openstack.common.apiclient import exceptions

from oslo_utils import uuidutils


class Component(apiclient_base.Resource):
    def __repr__(self):
        return "<Component %s>" % self._info


class ComponentManager(solum_base.CrudManager, solum_base.FindMixin):
    resource_class = Component
    collection_key = 'components'
    key = 'component'

    def list(self, **kwargs):
        return super(ComponentManager, self).list(base_url="/v1", **kwargs)

    def create(self, **kwargs):
        return super(ComponentManager, self).create(base_url="/v1", **kwargs)

    def get(self, **kwargs):
        return super(ComponentManager, self).get(base_url="/v1", **kwargs)

    def put(self, **kwargs):
        return super(ComponentManager, self).put(base_url="/v1", **kwargs)

    def find(self, **kwargs):
        if 'component_id' in kwargs:
            return super(ComponentManager, self).get(base_url="/v1", **kwargs)
        elif 'name_or_id' in kwargs:
            name_or_uuid = kwargs['name_or_id']
            try:
                if uuidutils.is_uuid_like(name_or_uuid):
                    return super(ComponentManager, self).get(
                        base_url="/v1",
                        component_id=name_or_uuid)
                else:
                    return super(ComponentManager, self).findone(
                        name=name_or_uuid)
            except exceptions.NoUniqueMatch:
                raise exc.NotUnique(resource='Component')
