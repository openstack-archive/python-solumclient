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

from solumclient.common import base as solum_base
from solumclient.openstack.common.apiclient import base as apiclient_base


class Requirement(apiclient_base.Resource):
    def __repr__(self):
        return "<Requirement %s>" % self._info


class ServiceReference(apiclient_base.Resource):
    def __repr__(self):
        return "<ServiceReference %s>" % self._info


class Artifact(apiclient_base.Resource):
    def __repr__(self):
        return "<Artifact %s>" % self._info

    def _add_requirements_details(self, req_list):
        return [Requirement(None, res, loaded=True)
                for res in req_list if req_list]

    def _add_details(self, info):
        for (k, v) in six.iteritems(info):
            try:
                if k == 'requirements':
                    v = self._add_requirements_details(v)
                setattr(self, k, v)
                self._info[k] = v
            except AttributeError:
                # In this case we already defined the attribute on the class
                pass


class Plan(apiclient_base.Resource):
    def __repr__(self):
        return "<Plan %s>" % self._info

    def _add_artifact_details(self, artf_list):
        return [Artifact(None, res, loaded=True)
                for res in artf_list if artf_list]

    def _add_services_details(self, serv_list):
        return [ServiceReference(None, res, loaded=True)
                for res in serv_list if serv_list]

    def _add_details(self, info):
        for (k, v) in six.iteritems(info):
            try:
                if k == 'artifacts':
                    v = self._add_artifact_details(v)
                elif k == 'services':
                    v = self._add_services_details(v)
                setattr(self, k, v)
                self._info[k] = v
            except AttributeError:
                # In this case we already defined the attribute on the class
                pass


class PlanManager(solum_base.CrudManager):
    resource_class = Plan
    collection_key = 'plans'
    key = 'plan'

    def list(self, **kwargs):
        return super(PlanManager, self).list(base_url="/v1", **kwargs)

    def create(self, plan, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        kwargs['data'] = plan
        kwargs.setdefault("headers", kwargs.get("headers", {}))
        kwargs['headers']['Content-Type'] = 'application/json'
        body = self.client.post(self.build_url(base_url="/v1", **kwargs),
                                **kwargs).json()
        return self.resource_class(self, body)

    def get(self, **kwargs):
        return super(PlanManager, self).get(base_url="/v1", **kwargs)

    def put(self, plan, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        kwargs['data'] = plan
        kwargs.setdefault("headers", kwargs.get("headers", {}))
        kwargs['headers']['Content-Type'] = 'application/json'
        body = self.client.put(self.build_url(base_url="/v1", **kwargs),
                               **kwargs).json()
        return self.resource_class(self, body)

    def delete(self, **kwargs):
        return super(PlanManager, self).delete(base_url="/v1", **kwargs)
