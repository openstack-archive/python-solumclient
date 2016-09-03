# Copyright 2015 - Rackspace
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


class Workflow(apiclient_base.Resource):
    def __repr__(self):
        return "<Workflow %s>" % self._info


class UserLog(apiclient_base.Resource):
    def __repr__(self):
        return "<Log %s>" % self._info


class WorkflowManager(solum_base.CrudManager, solum_base.FindMixin):
    resource_class = Workflow
    collection_key = 'workflows'
    key = 'workflow'

    def __init__(self, client, *args, **kwargs):
        super(WorkflowManager, self).__init__(client)
        self.app_id = kwargs.get('app_id')
        self.base_url = '/v1/apps/%s' % self.app_id

    def list(self, **kwargs):
        return (super(WorkflowManager, self).list(
                base_url=self.base_url, **kwargs))

    def create(self, **kwargs):
        # kwargs = self._filter_kwargs(kwargs)
        # kwargs['json'] = {'actions': actions}
        # post_url = self.build_url(base_url=self.base_url, **kwargs)
        # return self.client.create(post_url, **kwargs)
        return (super(WorkflowManager, self).create(
                base_url=self.base_url, **kwargs))

    def get(self, **kwargs):
        return (super(WorkflowManager, self).get(
                base_url=self.base_url, **kwargs))

    def logs(self, **kwargs):
        self.resource_class = UserLog
        url = self.build_url(self.base_url, **kwargs)
        rev_or_uuid = kwargs['revision_or_id']
        try:
            if uuidutils.is_uuid_like(rev_or_uuid):
                workflow_id = rev_or_uuid
            else:
                wf = self.find(**kwargs)
                workflow_id = wf.id
        except exceptions.NoUniqueMatch:
            raise exc.NotUnique(resource='Workflow')

        url += '/%s/logs/' % workflow_id
        return self._list(url)

    def find(self, **kwargs):
        if 'workflow_id' in kwargs:
            return (super(WorkflowManager, self).get(
                    base_url=self.base_url, **kwargs))
        elif 'revision_or_id' in kwargs:
            rev_or_uuid = kwargs['revision_or_id']
            try:
                if uuidutils.is_uuid_like(rev_or_uuid):
                    return super(WorkflowManager, self).get(
                        base_url=self.base_url,
                        workflow_id=rev_or_uuid)
                else:
                    return super(WorkflowManager, self).findone(
                        app_id=self.app_id, wf_id=rev_or_uuid)
            except exceptions.NoUniqueMatch:
                raise exc.NotUnique(resource='Workflow')
