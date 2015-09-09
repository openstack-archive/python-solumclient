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

from six.moves.urllib import parse as urlparse

from solumclient.openstack.common.apiclient import base
from solumclient.openstack.common.apiclient import exceptions


class FindMixin(object):
    """Just `findone()`/`findall()` methods.

    Note: this is largely a copy of apiclient.base.ManagerWithFind
          but without the inheritance and the find() method which
          does not clash with the Manager find() - now called findone().
    """

    def findone(self, **kwargs):
        """Find a single item with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        matches = self.findall(**kwargs)
        num_matches = len(matches)
        if num_matches == 0:
            msg = "No %s matching %s." % (self.resource_class.__name__, kwargs)
            raise exceptions.NotFound(msg)
        elif num_matches > 1:
            raise exceptions.NoUniqueMatch()
        else:
            return matches[0]

    def findall(self, **kwargs):
        """Find all items with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        found = []
        searches = kwargs.items()

        for obj in self.list():
            try:
                if all(getattr(obj, attr) == value
                       for (attr, value) in searches):
                    found.append(obj)
            except AttributeError:
                continue

        return found


class CrudManager(base.CrudManager):
    def list(self, base_url=None, **kwargs):
        """List the collection.

        :param base_url: if provided, the generated URL will be appended to it
        """
        kwargs = self._filter_kwargs(kwargs)

        return self._list(
            '%(base_url)s%(query)s' % {
                'base_url': self.build_url(base_url=base_url, **kwargs),
                'query': '?%s' % urlparse.urlencode(kwargs) if kwargs else '',
            })

    def get(self, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        return self._get(
            self.build_url(**kwargs))

    def create(self, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        return self._post(
            self.build_url(**kwargs), kwargs)

    def update(self, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        params = kwargs.copy()
        params.pop('%s_id' % self.key)

        return self._put(
            self.build_url(**kwargs), params)

    def patch(self, **kwargs):
        kwargs = self._filter_kwargs(kwargs)
        params = kwargs.copy()
        params.pop('%s_id' % self.key)
        params.pop('base_url')

        return self._patch(
            self.build_url(**kwargs), params)
