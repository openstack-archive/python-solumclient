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
from solumclient.common import exc
from solumclient.common import yamlutils
from solumclient.openstack.common.apiclient import base as apiclient_base
from solumclient.openstack.common.apiclient import exceptions

from oslo_utils import uuidutils


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


class PlanManager(solum_base.CrudManager, solum_base.FindMixin):
    resource_class = Plan
    collection_key = 'plans'
    key = 'plan'

    def list(self, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        kwargs.setdefault("headers", kwargs.get("headers", {}))
        kwargs['headers']['Content-Type'] = 'x-application/yaml'
        resp = self.client.get(
            self.build_url(base_url="/v1", **kwargs), **kwargs)
        try:
            resp_plan = yamlutils.load(resp.content)
        except ValueError as e:
            raise exc.CommandException(message='Could not load Plan. '
                                       'Reason: %s' % e.message)
        return [Plan(self, res, loaded=True) for res in resp_plan if res]

    def create(self, plan, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        kwargs['data'] = plan
        kwargs.setdefault("headers", kwargs.get("headers", {}))
        kwargs['headers']['Content-Type'] = 'x-application/yaml'
        try:
            resp = self.client.post(
                self.build_url(base_url="/v1", **kwargs), **kwargs)
        except Exception as e:
            message = vars(e).get('details', str(e))
            raise exceptions.BadRequest(message=message)
        try:
            resp_plan = yamlutils.load(resp.content)
        except ValueError as e:
            raise exc.CommandException(message='Could not load Plan. '
                                       'Reason: %s' % e.message)
        return Plan(self, resp_plan)

    def _get(self, url, response_key=None):
        kwargs = {'headers': {}}
        kwargs['headers']['Content-Type'] = 'x-application/yaml'
        resp = self.client.get(url, **kwargs)
        try:
            resp_plan = yamlutils.load(resp.content)
        except ValueError as e:
            raise exc.CommandException(message='Could not load Plan. '
                                       'Reason: %s' % e.message)

        return Plan(self, resp_plan, loaded=True)

    def get(self, **kwargs):
        return super(PlanManager, self).get(base_url="/v1", **kwargs)

    def find(self, **kwargs):
        if 'plan_id' in kwargs:
            return super(PlanManager, self).get(base_url="/v1", **kwargs)
        elif 'name_or_id' in kwargs:
            name_or_uuid = kwargs['name_or_id']
            try:
                if uuidutils.is_uuid_like(name_or_uuid):
                    return super(PlanManager, self).get(base_url="/v1",
                                                        plan_id=name_or_uuid)
                else:
                    return super(PlanManager, self).findone(name=name_or_uuid)
            except exceptions.NoUniqueMatch:
                raise exc.NotUnique(resource='Plan')

    def update(self, plan, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        kwargs['data'] = plan
        kwargs.setdefault("headers", kwargs.get("headers", {}))
        kwargs['headers']['Content-Type'] = 'x-application/yaml'
        resp = self.client.put(self.build_url(base_url="/v1", **kwargs),
                               **kwargs)
        try:
            resp_plan = yamlutils.load(resp.content)
        except ValueError as e:
            raise exc.CommandException(message='Could not load Plan. '
                                       'Reason: %s' % e.message)
        return self.resource_class(self, resp_plan)

    def delete(self, **kwargs):
        return super(PlanManager, self).delete(base_url="/v1", **kwargs)
