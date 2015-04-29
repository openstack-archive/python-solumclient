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
import re
import sys
import uuid

import fixtures
import mock
import six
from stevedore import extension
from testtools import matchers

from solumclient import client
from solumclient.common import yamlutils
from solumclient.openstack.common.apiclient import auth
from solumclient import solum
from solumclient.tests import base
from solumclient.v1 import assembly
from solumclient.v1 import component
from solumclient.v1 import languagepack
from solumclient.v1 import pipeline
from solumclient.v1 import plan

FAKE_ENV = {'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where'}

languagepack_file_data = (
    '{"language-pack-type":"Java", "language-pack-name":"Java version 1.4."}')


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
    def shell(self, argstr, mock_mgr_map, exit_code=0):
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
            self.assertEqual(exit_code, exc_value.code)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out

    def test_get_client_debug(self):
        self.make_env()
        test_client = client.get_client('1')
        self.assertFalse(test_client.http_client.debug)
        test_client = client.get_client('1', debug=True)
        self.assertTrue(test_client.http_client.debug)

    def test_get_client_insecure(self):
        self.make_env()
        test_client = client.get_client('1')
        self.assertTrue(test_client.http_client.verify)
        test_client = client.get_client('1', verify=False)
        self.assertFalse(test_client.http_client.verify)

    def test_help(self):
        required = [
            '.*?^Available commands:'

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
        self.shell("assembly create assembly_name http://example.com/a.yaml")
        mock_assembly_create.assert_called_once_with(
            name='assembly_name',
            description=None,
            plan_uri='http://example.com/a.yaml')

    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_with_bogus_params(self, mock_assembly_create):
        self.make_env()
        self.shell("assembly create app_name http://example.com/a.yaml "
                   "--BOGUS=False",
                   exit_code=2)

    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_without_name(self, mock_assembly_create):
        self.make_env()
        self.shell("assembly create http://example.com/a.yaml",
                   exit_code=2)

    @mock.patch.object(plan.PlanManager, "find")
    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_with_plan_name(self, mock_assembly_create,
                                            mock_plan_find):
        class FakePlan(object):
            uri = 'http://example.com/the-plan.yaml'

        self.make_env()
        mock_plan_find.return_value = FakePlan()
        self.shell("assembly create assembly_name the-plan-name")
        mock_plan_find.assert_called_once_with(name_or_id='the-plan-name')
        mock_assembly_create.assert_called_once_with(
            name='assembly_name',
            description=None,
            plan_uri='http://example.com/the-plan.yaml')

    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_with_description(self, mock_assembly_create):
        self.make_env()
        self.shell("""assembly create assembly_name http://example.com/a.yaml
                  --description=description""")
        mock_assembly_create.assert_called_once_with(
            name='assembly_name',
            description='description',
            plan_uri='http://example.com/a.yaml')

    @mock.patch.object(assembly.AssemblyManager, "create")
    def test_assembly_create_without_description(self, mock_assembly_create):
        self.make_env()
        self.shell("assembly create assembly_name http://example.com/a.yaml")
        mock_assembly_create.assert_called_once_with(
            name='assembly_name',
            description=None,
            plan_uri='http://example.com/a.yaml')

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

    # Pipeline Tests #
    @mock.patch.object(pipeline.PipelineManager, "list")
    def test_pipeline_list(self, mock_pipeline_list):
        self.make_env()
        self.shell("pipeline list")
        mock_pipeline_list.assert_called_once_with()

    @mock.patch.object(pipeline.PipelineManager, "create")
    def test_pipeline_create(self, mock_pipeline_create):
        self.make_env()
        self.shell("pipeline create http://example.com/a.yaml workbook test")
        mock_pipeline_create.assert_called_once_with(
            name='test',
            workbook_name='workbook',
            plan_uri='http://example.com/a.yaml')

    @mock.patch.object(pipeline.PipelineManager, "create")
    def test_pipeline_create_without_name(self, mock_pipeline_create):
        self.make_env()
        self.shell("pipeline create http://example.com/a.yaml workbook",
                   exit_code=2)

    @mock.patch.object(plan.PlanManager, "find")
    @mock.patch.object(pipeline.PipelineManager, "create")
    def test_pipeline_create_with_plan_name(self, mock_pipeline_create,
                                            mock_plan_find):
        class FakePlan(object):
            uri = 'http://example.com/the-plan.yaml'

        self.make_env()
        mock_plan_find.return_value = FakePlan()
        self.shell("pipeline create the-plan-name workbook test")
        mock_plan_find.assert_called_once_with(name_or_id='the-plan-name')
        mock_pipeline_create.assert_called_once_with(
            name='test',
            workbook_name='workbook',
            plan_uri='http://example.com/the-plan.yaml')

    @mock.patch.object(pipeline.PipelineManager, "delete")
    @mock.patch.object(pipeline.PipelineManager, "find")
    def test_pipeline_delete(self, mock_pipeline_find, mock_pipeline_delete):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("pipeline delete %s" % the_id)
        mock_pipeline_find.assert_called_once_with(
            name_or_id=the_id)
        mock_pipeline_delete.assert_called_once()

    @mock.patch.object(pipeline.PipelineManager, "find")
    def test_pipeline_get(self, mock_pipeline_find):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("pipeline show %s" % the_id)
        mock_pipeline_find.assert_called_once_with(name_or_id=the_id)

    @mock.patch.object(pipeline.PipelineManager, "find")
    def test_pipeline_get_by_name(self, mock_pipeline_find):
        self.make_env()
        self.shell("pipeline show app2")
        mock_pipeline_find.assert_called_once_with(name_or_id='app2')

    # App Tests #
    def test_app_create_with_missing_artifacts(self):
        raw_data = 'version: 1\nname: ex_plan1\ndescription: dsc1.'
        mopen = mock.mock_open(read_data=raw_data)

        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            out = self.shell("app create --plan-file /dev/null")
            self.assertEqual("ERROR: Missing artifacts section\n", out)

    def test_app_create_with_bad_name(self):
        raw_data = '\n'.join([
            'version: 1',
            'name: ex=plan1',
            'description: python web app',
            'artifacts:',
            '- name: web',
            '  content:',
            '    href: https://github.com/user/repo.git',
            '  language_pack: auto',
            '  unittest_cmd: ./unit_tests.sh',
            '  run_cmd: python app.py',
            '  ports: 5000'])

        mopen = mock.mock_open(read_data=raw_data)

        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            out = self.shell("app create --plan-file /dev/null")

            self.assertEqual("ERROR: Application name must be 1-100 "
                             "characters and must only contain "
                             "a-z,A-Z,0-9,-,_\n", out)

    def test_app_create_with_bad_artifact_name(self):
        raw_data = '\n'.join([
            'version: 1',
            'name: explan1',
            'description: python web app',
            'artifacts:',
            '- name:',
            '  content:',
            '    href: https://github.com/user/repo.git',
            '  language_pack: auto',
            '  unittest_cmd: ./unit_tests.sh',
            '  run_cmd: python app.py',
            '  ports: 5000'])

        mopen = mock.mock_open(read_data=raw_data)

        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            out = self.shell("app create --plan-file /dev/null")

            # No part of the plan is in error; the next step in the test
            # is authorization, which is deliberately mocked.
            self.assertEqual("ERROR: "
                             "Authorization Failed: Unable to establish "
                             "connection to http://no.where/tokens\n", out)

    def test_app_create_with_artifacts_empty(self):
        raw_data = 'version: 1\nname: ex_plan1\ndescription: dsc1.\nartifacts:'
        mopen = mock.mock_open(read_data=raw_data)

        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            out = self.shell("app create --plan-file /dev/null")
            self.assertEqual("ERROR: Artifacts cannot be empty\n", out)

    def test_app_create_with_artifacts_no_content(self):
        raw_data = 'version: 1\nname: ex_plan1\ndescription: d1.\nartifacts:\n'
        raw_data += '- name: asdfds\n'
        raw_data += '  artifact_type: heroku\n'
        raw_data += '  language_pack: lp'

        mopen = mock.mock_open(read_data=raw_data)

        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            out = self.shell("app create --plan-file /dev/null")
            self.assertEqual("ERROR: Artifact content missing\n", out)

    def test_app_logs_need_an_identifier(self):
        self.make_env()
        out = self.shell("app logs")
        self.assertEqual("ERROR: You must specify an application.\n", out)

    # Plan Tests #
    @mock.patch.object(plan.PlanManager, "create")
    def test_plan_create(self, mock_plan_create):
        FakeResource = collections.namedtuple("FakeResource",
                                              "uuid name description uri")

        mock_plan_create.return_value = FakeResource('foo', 'foo', 'foo',
                                                     'foo')
        raw_data = 'version: 1\nname: ex_plan1\ndescription: dsc1.'
        plan_data = yamlutils.dump(yamlutils.load(raw_data))
        mopen = mock.mock_open(read_data=raw_data)
        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            self.shell("plan create /dev/null")
            mock_plan_create.assert_called_once_with(plan_data)

    @mock.patch.object(solum, "show_public_keys")
    @mock.patch.object(plan.PlanManager, "create")
    def test_plan_create_with_private_github_repo(self, mock_plan_create,
                                                  mock_show_pub_keys):
        FakeResource = collections.namedtuple(
            "FakeResource", "uuid name description uri artifacts")

        mock_plan_create.return_value = FakeResource('foo', 'foo', 'foo',
                                                     'foo', 'artifacts')
        expected_printed_dict_args = vars(mock_plan_create.return_value)
        expected_printed_dict_args.pop('artifacts')
        expected_show_pub_keys_args = 'artifacts'
        raw_data = 'version: 1\nname: ex_plan1\ndescription: dsc1.'
        plan_data = yamlutils.dump(yamlutils.load(raw_data))
        mopen = mock.mock_open(read_data=raw_data)
        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()
            self.shell("plan create /dev/null")
            mock_plan_create.assert_called_once_with(plan_data)
            mock_show_pub_keys.assert_called_once_with(
                expected_show_pub_keys_args)

    @mock.patch.object(plan.PlanManager, "list")
    def test_plan_list(self, mock_plan_list):
        self.make_env()
        self.shell("plan list")
        mock_plan_list.assert_called_once_with()

    @mock.patch.object(plan.PlanManager, "delete")
    @mock.patch.object(plan.PlanManager, "find")
    def test_plan_delete(self, mock_plan_find, mock_plan_delete):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("plan delete %s" % the_id)
        mock_plan_find.assert_called_once_with(name_or_id=the_id)
        mock_plan_delete.assert_called_once()

    @mock.patch.object(plan.PlanManager, "find")
    def test_plan_get(self, mock_plan_find):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("plan show %s" % the_id)
        mock_plan_find.assert_called_once_with(name_or_id=the_id)

    @mock.patch.object(solum, "show_public_keys")
    @mock.patch.object(plan.PlanManager, "find")
    def test_plan_get_private_github_repo(self, mock_plan_find,
                                          mock_show_pub_keys):
        self.make_env()
        the_id = str(uuid.uuid4())
        FakeResource = collections.namedtuple(
            "FakeResource", "uuid name description uri artifacts")
        mock_plan_find.return_value = FakeResource('foo', 'foo', 'foo', 'foo',
                                                   'artifacts')
        expected_show_pub_keys_args = 'artifacts'
        self.shell("plan show %s" % the_id)
        mock_plan_find.assert_called_once_with(name_or_id=the_id)
        mock_show_pub_keys.assert_called_once_with(
            expected_show_pub_keys_args)

    # LanguagePack Tests #
    @mock.patch.object(languagepack.LanguagePackManager, "list")
    def test_languagepack_list(self, mock_lp_list):
        self.make_env()
        self.shell("languagepack list")
        mock_lp_list.assert_called_once()

    @mock.patch.object(languagepack.LanguagePackManager, "create")
    def test_languagepack_create(self, mock_lp_create):
        FakeResource = collections.namedtuple("FakeResource",
                                              "uuid name description "
                                              "compiler_versions os_platform")
        mock_lp_create.return_value = FakeResource(
            'foo', 'foo', 'foo', 'foo', 'foo')
        lp_metadata = '{"OS": "Ubuntu"}'
        mopen = mock.mock_open(read_data=lp_metadata)
        with mock.patch('%s.open' % solum.__name__, mopen, create=True):
            self.make_env()

            self.shell("languagepack create lp_name github.com/test "
                       "--lp_metadata=/dev/null")
            mock_lp_create.assert_called_once_with(
                name='lp_name',
                source_uri='github.com/test',
                lp_metadata=lp_metadata)

    @mock.patch.object(languagepack.LanguagePackManager, "delete")
    def test_languagepack_delete(self, mock_lp_delete):
        self.make_env()
        self.shell("languagepack delete fake-lp-id")
        mock_lp_delete.assert_called_once_with(lp_id='fake-lp-id')

    @mock.patch.object(languagepack.LanguagePackManager, "find")
    def test_languagepack_get(self, mock_lp_get):
        self.make_env()
        self.shell("languagepack show fake-lp-id1")
        mock_lp_get.assert_called_once_with(name_or_id='fake-lp-id1')

    # Component Tests #
    @mock.patch.object(component.ComponentManager, "list")
    def test_component_list(self, mock_component_list):
        self.make_env()
        self.shell("component list")
        mock_component_list.assert_called_once_with()

    @mock.patch.object(component.ComponentManager, "find")
    def test_component_get(self, mock_component_find):
        self.make_env()
        the_id = str(uuid.uuid4())
        self.shell("component show %s" % the_id)
        mock_component_find.assert_called_once_with(name_or_id=the_id)

    @mock.patch.object(component.ComponentManager, "find")
    def test_component_get_by_name(self, mock_component_find):
        self.make_env()
        self.shell("component show comp1")
        mock_component_find.assert_called_once_with(name_or_id='comp1')

    def test_transform_git_url(self):
        private_uri = 'git@github.com:solum/python.git'
        public_uri = 'https://github.com/solum/python.git'
        private = True
        public = False

        result = solum.transform_git_url(private_uri, private)
        self.assertEqual(result, private_uri)

        result = solum.transform_git_url(public_uri, private)
        self.assertEqual(result, private_uri)

        result = solum.transform_git_url(private_uri, public)
        self.assertEqual(result, public_uri)

        result = solum.transform_git_url(public_uri, public)
        self.assertEqual(result, public_uri)
