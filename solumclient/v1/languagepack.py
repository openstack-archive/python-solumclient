# Copyright 2014 - Rackspace
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
from solumclient.openstack.common.apiclient import base as apiclient_base


class LanguagePack(apiclient_base.Resource):
    def __repr__(self):
        return "<LanguagePack %s>" % self._info


class UserLog(apiclient_base.Resource):
    def __repr__(self):
        return "<Log %s>" % self._info


class LanguagePackManager(solum_base.CrudManager):
    resource_class = LanguagePack
    collection_key = 'language_packs'
    key = 'lp'

    def list(self, **kwargs):
        return super(LanguagePackManager, self).list(base_url="/v1", **kwargs)

    def create(self, **kwargs):
        return super(LanguagePackManager,
                     self).create(base_url="/v1", **kwargs)

    def get(self, **kwargs):
        return super(LanguagePackManager,
                     self).get(base_url="/v1", **kwargs)

    def delete(self, **kwargs):
        return super(LanguagePackManager,
                     self).delete(base_url="/v1", **kwargs)

    def find(self, **kwargs):
        name_or_uuid = kwargs['name_or_id']
        return super(LanguagePackManager, self).get(base_url="/v1",
                                                    lp_id=name_or_uuid)

    def logs(self, **kwargs):
        self.resource_class = UserLog
        languagepack = self.find(name_or_id=kwargs['lp_id'])
        kwargs['lp_id'] = languagepack.uuid
        url = self.build_url(base_url="/v1", **kwargs)
        url += '/logs/'
        return self._list(url)
