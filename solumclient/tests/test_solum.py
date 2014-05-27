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

import collections
import json
import re
import sys
import uuid
import yaml

import fixtures
import mock
import six
from stevedore import extension
from testtools import matchers

from solumclient.openstack.common.apiclient import auth
from solumclient.openstack.common import cliutils
from solumclient import solum
from solumclient.tests import base
from solumclient.v1 import assembly
from solumclient.v1 import languagepack
from solumclient.v1 import plan

FAKE_ENV = {'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where'}

plan_file_data = (
    'name: ex1\n'
    'description: Nodejs express.\n'
    'artifacts:\n'
    '- name: nodeus\n'
    '  artifact_type: application.heroku\n'
    '  content:\n'
    '    href: https://github.com/paulczar/example-nodejs-express.git\n'
    '  language_pack: auto')


class MockEntrypoint(object):
    def __init__(self, name, plugin):
        self.name = name
        self.plugin = plugin


class BaseFakePlugin(auth.BaseAuthPlugin):
    def _do_authenticate(self, http_client):
        pass

    def token_and_endpoint(self, endpoint_type, service_type):
        pass


class TestSolum(base.TestCase):
    """Test the Solum CLI."""

    re_options = re.DOTALL | re.MULTILINE

    # Patch os.environ to avoid required auth info.
    def make_env(self, exclude=None):
        env = dict((k, v) for k, v in FAKE_ENV.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    @mock.patch.object(extension.ExtensionManager, "map")
    def shell(self, argstr, mock_mgr_map):
        class FakePlugin(BaseFakePlugin):
            def authenticate(self, cls):
                cls.request(
                    "POST", "http://auth/tokens",
                    json={"fake": "me"}, allow_redirects=True)

        mock_mgr_map.side_effect = (
            lambda func: func(MockEntrypoint("fake", FakePlugin)))

        orig = sys.stdout
        try:
            sys.stdout = six.StringIO()
            argv = [__file__, ]
            argv.extend(argstr.split())
            self.useFixture(
                fixtures.MonkeyPatch('sys.argv', argv))
            solum.main()
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(0, exc_value.code)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out

    def test_help(self):
        required = [
            '.*?^usage:'
            '.*?^positional arguments'
            '.*?^optional arguments'

        ]
        help_text = self.shell('--help')
        for r in required:
            self.assertThat(help_text,
                            matchers.MatchesRegex(r,
                                                  self.re_options))

    # Assembly Tests #
    @mock.patch.object(assembly.AssemblyManager, "list")
    def test_assembly_list(self, mock_assembly_list):
        self.make_env()
        self.shell("assembly list")
        mock_assembly_list.assert_called_once_with()

    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create(self, mock_assembly_create):
        self.make_env()
        self.shell("assembly create http://example.com/a.yaml --assembly=test")
        mock_assembly_create.assert_called_once_with(
            name='test',
            plan_uri='http://example.com/a.yaml')

    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_without_name(self, mock_assembly_create):
        self.make_env()
        self.shell("assembly create http://example.com/a.yaml")
        mock_assembly_create.assert_called_once_with(
            name=None,
            plan_uri='http://example.com/a.yaml')

    @mock.patch.object(plan.PlanManager, "find")
    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_with_plan_name(self, mock_assembly_create,
                                            mock_app_find):
        class FakePlan(object):
            uri = 'http://example.com/the-plan.yaml'

        self.make_env()
        mock_app_find.return_value = FakePlan()
        self.shell("assembly create the-plan-name --assembly=test")
        mock_app_find.assert_called_once_with(name_or_id='the-plan-name')
        mock_assembly_create.assert_called_once_with(
            name='test',
            plan_uri='http://example.com/the-plan.yaml')

    @mock.patch.object(assembly.AssemblyManager, "delete")
    @mock.patch.object(assembly.AssemblyManager, "find")
    def test_assembly_delete(self, mock_assembly_find, mock_assembly_delete):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("assembly delete %s" % the_id)
        mock_assembly_find.assert_called_once_with(
            name_or_id=the_id)
        mock_assembly_delete.assert_called_once()

    @mock.patch.object(assembly.AssemblyManager, "find")
    def test_assembly_get(self, mock_assembly_find):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("assembly show %s" % the_id)
        mock_assembly_find.assert_called_once_with(name_or_id=the_id)

    @mock.patch.object(assembly.AssemblyManager, "find")
    def test_assembly_get_by_name(self, mock_assembly_find):
        self.make_env()
        self.shell("assembly show app2")
        mock_assembly_find.assert_called_once_with(name_or_id='app2')

    # Plan Tests #
    @mock.patch.object(cliutils, "print_dict")
    @mock.patch.object(plan.PlanManager, "create")
    def test_app_create(self, mock_app_create, mock_print_dict):
        FakeResource = collections.namedtuple("FakeResource",
                                              "uuid name description uri")

        mock_app_create.return_value = FakeResource('foo', 'foo', 'foo', 'foo')
        expected_printed_dict_args = mock_app_create.return_value._asdict()
        plan_data = yaml.load(plan_file_data)
        mopen = mock.mock_open(read_data=plan_file_data)
        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            self.shell("app create /dev/null")
            mock_app_create.assert_called_once_with(**plan_data)
            mock_print_dict.assert_called_once_with(
                expected_printed_dict_args,
                wrap=72)

    @mock.patch.object(plan.PlanManager, "list")
    def test_app_list(self, mock_app_list):
        self.make_env()
        self.shell("app list")
        mock_app_list.assert_called_once_with()

    @mock.patch.object(plan.PlanManager, "delete")
    @mock.patch.object(plan.PlanManager, "find")
    def test_app_delete(self, mock_app_find, mock_app_delete):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("app delete %s" % the_id)
        mock_app_find.assert_called_once_with(name_or_id=the_id)
        mock_app_delete.assert_called_once()

    @mock.patch.object(plan.PlanManager, "find")
    def test_app_get(self, mock_app_find):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("app show %s" % the_id)
        mock_app_find.assert_called_once_with(name_or_id=the_id)

    # LanguagePack Tests #
    @mock.patch.object(languagepack.LanguagePackManager, "list")
    def test_languagepack_list(self, mock_lp_list):
        self.make_env()
        self.shell("languagepack list")
        mock_lp_list.assert_called_once()

    @mock.patch.object(json, "load")
    @mock.patch.object(languagepack.LanguagePackManager, "create")
    def test_languagepack_create(self, mock_lp_create, mock_json_load):
        mock_json_load.side_effect = """{
            "language-pack-type": "Java",
            "language-pack-name": "Java version 1.4.",
            }"""
        self.make_env()
        self.shell("languagepack create /dev/null")
        mock_lp_create.assert_called_once()

    @mock.patch.object(languagepack.LanguagePackManager, "delete")
    def test_languagepack_delete(self, mock_lp_delete):
        self.make_env()
        self.shell("languagepack delete fake-lp-id")
        mock_lp_delete.assert_called_once_with(lp_id='fake-lp-id')

    @mock.patch.object(languagepack.LanguagePackManager, "get")
    def test_languagepack_get(self, mock_lp_get):
        self.make_env()
        self.shell("languagepack show fake-lp-id1")
        mock_lp_get.assert_called_once_with(lp_id='fake-lp-id1')
