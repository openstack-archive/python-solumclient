# Copyright (c) 2014 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Initial M1 Solum CLI commands implemented (but not REST communications):
* plan create --repo="repo_url" [--build=no] plan_name
* plan delete plan_name
* plan list
* plan show plan_id
* languagepack create <NAME> <GIT_REPO_URL>
* languagepack list
* languagepack show <LP_ID>
* languagepack delete <LP_ID>
* languagepack logs <LP_ID>
* component list


Notes:
* This code is expected to be replaced by the OpenStack Client (OSC) when
    it has progressed a little bit farther as described at:
    https://wiki.openstack.org/wiki/Solum/CLI
* Internationalization will not be added in M1 since this is a prototype
"""

from __future__ import print_function

import argparse
import copy
import json
import re
import sys

import httplib2
import jsonschema
from keystoneclient.v2_0 import client as keystoneclient
import six

import solumclient
from solumclient.common import cli_utils
from solumclient.common import exc
from solumclient.common import github
from solumclient.common import yamlutils
from solumclient import config
from solumclient.openstack.common.apiclient import exceptions
from solumclient.v1 import app as cli_app
from solumclient.v1 import languagepack as cli_lp
from solumclient.v1 import pipeline as cli_pipe
from solumclient.v1 import plan as cli_plan
from solumclient.v1 import workflow as cli_wf


def name_error_message(name_type):
    return name_type + (" must be 1-100 characters long, only "
                        "contain a-z,0-9,-,_ and start with "
                        "an alphabet character.")


def name_is_valid(string):
    if not string or not string[0].isalpha():
        return False

    try:
        re.match(r'^([a-z0-9-_]{1,100})$', string).group(0)
    except AttributeError:
        return False
    return True


def ValidName(string):
    if not name_is_valid(string):
        raise AttributeError(name_error_message("Names"))
    return string


def lpname_is_valid(string):
    return name_is_valid(string)


def ValidLPName(string):
    if not lpname_is_valid(string):
        raise AttributeError(name_error_message("LP names"))
    return string


def ValidPort(string):
    try:
        port_val = int(string)
        if 1 <= port_val <= 65535:
            return port_val
        else:
            raise ValueError
    except ValueError:
        raise AttributeError("The port should be an integer between 1 and "
                             "65535")


def transform_git_url(git_url, private):
    # try to use a correct git uri
    pt = re.compile(r'github\.com[:/](.+?)/(.+?)($|/.*$|\.git$|\.git/.*$)')
    match = pt.search(git_url)
    if match:
        user_org_name = match.group(1)
        repo = match.group(2)
        if private:
            right_uri = 'git@github.com:%s/%s.git' % (user_org_name, repo)
        else:
            right_uri = 'https://github.com/%s/%s.git' % (user_org_name, repo)
        return right_uri
    else:
        msg = "Provide the git uri in the following format: "
        if not private:
            msg = msg + "https://github.com/<USER>/<REPO>.git"
        else:
            msg = msg + "git@github.com:<USER>/<REPO>.git"
        raise exc.CommandError(message=msg)


def show_public_keys(artifacts):
    public_keys = {}
    if artifacts:
        for arti in artifacts:
            if arti.content and ('public_key' in arti.content):
                public_keys.update(
                    {arti.content['href']: arti.content['public_key']})
    if public_keys:
        print('Important:')
        print('  Solum has generated and uploaded SSH keypair for your ' +
              'private github repository/ies.')
        print('  You may need to add these public SSH keys as github ' +
              'deploy keys, if they were not uploaded successfully.')
        print('  This enables solum to securely ' +
              'clone/pull your private repository/ies.')
        print('  More details on github deploy keys: ' +
              'https://developer.github.com/guides/' +
              'managing-deploy-keys/#deploy-keys\n')
        for href, pub_key in public_keys.items():
            print('%s :\n  %s' % (href, pub_key))


class PlanCommands(cli_utils.CommandsBase):
    """Commands for working with plans.

Available commands:

    solum plan list
        Print an index of all available plans.

    solum plan show <PLAN>
        Print details about a plan.

    solum plan create <PLANFILE> [--param-file <PARAMFILE>]
        Register a plan with Solum.

    solum plan delete <PLAN>
        Destroy a plan. Plans with dependent assemblies cannot be deleted.
    """

    def create(self):
        """Create a plan."""
        self.parser.add_argument('plan_file',
                                 help="A yaml file that defines a plan,"
                                      " check out solum repo for examples")
        self.parser.add_argument('--param-file',
                                 dest='param_file',
                                 help="A yaml file containing custom"
                                      " parameters to be used in the"
                                      " application, check out solum repo for"
                                      " examples")

        self.parser._names['plan_file'] = 'plan file'
        args = self.parser.parse_args()
        try:
            with open(args.plan_file) as definition_file:
                plan_definition = definition_file.read()
                definition = yamlutils.load(plan_definition)
        except IOError:
            message = "Could not open plan file %s." % args.plan_file
            raise exc.CommandError(message=message)
        except ValueError:
            message = ("Plan file %s was not a valid YAML mapping." %
                       args.plan_file)
            raise exc.CommandError(message=message)

        if args.param_file:
            try:
                with open(args.param_file) as param_f:
                    param_definition = param_f.read()
                definition['parameters'] = yamlutils.load(param_definition)
            except IOError:
                message = "Could not open param file %s." % args.param_file
                raise exc.CommandError(message=message)
            except ValueError:
                message = ("Param file %s was not a valid YAML mapping." %
                           args.param_file)
                raise exc.CommandError(message=message)
        plan = self.client.plans.create(yamlutils.dump(definition))
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts']
        artifacts = copy.deepcopy(vars(plan).get('artifacts'))
        self._print_dict(plan, fields, wrap=72)
        show_public_keys(artifacts)

    def delete(self):
        """Delete a plan."""
        self.parser.add_argument('plan_uuid',
                                 help="Tenant/project-wide unique "
                                 "plan uuid or name")
        self.parser._names['plan_uuid'] = 'plan'
        args = self.parser.parse_args()
        plan = self.client.plans.find(name_or_id=args.plan_uuid)
        cli_plan.PlanManager(self.client).delete(plan_id=str(plan.uuid))

    def show(self):
        """Show a plan's resource."""
        self.parser.add_argument('plan_uuid',
                                 help="Plan uuid or name")
        self.parser._names['plan_uuid'] = 'plan'
        args = self.parser.parse_args()
        plan = self.client.plans.find(name_or_id=args.plan_uuid)
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts']
        artifacts = copy.deepcopy(vars(plan).get('artifacts'))
        self._print_dict(plan, fields, wrap=72)
        show_public_keys(artifacts)

    def list(self):
        """List all plans."""
        fields = ['uuid', 'name', 'description']
        plans = self.client.plans.list()
        self._print_list(plans, fields)


class ComponentCommands(cli_utils.CommandsBase):
    """Commands for working with components.

Available commands:

    solum component list
        Print an index of all available components.

    solum component show <UUID>
        Print details about a component.

    """

    def show(self):
        """Show a component's resource."""
        self.parser.add_argument('component_uuid',
                                 help="Component uuid or name")
        self.parser._names['component_uuid'] = 'component'
        args = self.parser.parse_args()
        component = self.client.components.find(name_or_id=args.component_uuid)
        fields = ['uuid', 'name', 'description', 'uri', 'assembly_uuid']
        self._print_dict(component, fields, wrap=72)

    def list(self):
        """List all components."""
        fields = ['uuid', 'name', 'description', 'assembly_uuid']
        components = self.client.components.list()
        self._print_list(components, fields)


class PipelineCommands(cli_utils.CommandsBase):
    """Commands for working with pipelines.

Available commands:

    solum pipeline list
        Print an index of all available pipelines.

    solum pipeline show <PIPELINE>
        Print details about a pipeline.

    solum pipeline create <PLAN_URI> <WORKBOOK_NAME> <NAME>
        Create a pipeline from a given workbook and registered plan.

    solum pipeline delete <PIPELINE>
        Destroy a pipeline.
    """

    def create(self):
        """Create a pipeline."""
        self.parser.add_argument('plan_uri',
                                 help="Tenant/project-wide unique "
                                 "plan (uri/uuid or name)")
        self.parser.add_argument('workbook_name',
                                 help="Workbook name")
        self.parser.add_argument('name',
                                 type=ValidName,
                                 help="Pipeline name")
        self.parser._names['plan_uri'] = 'plan URI'
        self.parser._names['workbook_name'] = 'workbook'
        args = self.parser.parse_args()
        plan_uri = args.plan_uri
        if '/' not in plan_uri:
            # might be a plan uuid/name
            # let's try and be helpful and get the real plan_uri.
            plan = self.client.plans.find(name_or_id=args.plan_uri)
            plan_uri = plan.uri
            print('Note: using plan_uri=%s' % plan_uri)

        pipeline = self.client.pipelines.create(
            name=args.name,
            plan_uri=plan_uri,
            workbook_name=args.workbook_name)
        fields = ['uuid', 'name', 'description',
                  'trigger_uri']
        self._print_dict(pipeline, fields, wrap=72)

    def delete(self):
        """Delete an pipeline."""
        self.parser.add_argument('pipeline_uuid',
                                 help="Pipeline uuid or name")
        self.parser._names['pipeline_uuid'] = 'pipeline'
        args = self.parser.parse_args()
        pipeline = self.client.pipelines.find(name_or_id=args.pipeline_uuid)
        cli_pipe.PipelineManager(self.client).delete(
            pipeline_id=str(pipeline.uuid))

    def list(self):
        """List all pipelines."""
        fields = ['uuid', 'name', 'description']
        pipelines = self.client.pipelines.list()
        self._print_list(pipelines, fields)

    def show(self):
        """Show a pipeline's resource."""
        self.parser.add_argument('pipeline_uuid',
                                 help="Pipeline uuid or name")
        self.parser._names['pipeline_uuid'] = 'pipeline'
        args = self.parser.parse_args()
        pipelines = self.client.pipelines.find(name_or_id=args.pipeline_uuid)
        fields = ['uuid', 'name', 'description',
                  'trigger_uri', 'workbook_name', 'last_execution']
        self._print_dict(pipelines, fields, wrap=72)


class LanguagePackCommands(cli_utils.CommandsBase):
    """Commands for working with language packs.

Available commands:

    solum lp create <NAME> <GIT_REPO_URL> [--param-file <param-file-name>]
        Create a new language pack from a git repo.
        You can pass an optional parameter file containing a dictionary.
        One use of the parameter file is to pass in credentials for
        infrastructure that should be used to build the lp.

    solum lp list
        Print and index of all available language packs.

    solum lp show <NAME|UUID>
        Print the details of a language pack.

    solum lp delete <NAME|UUID>
        Destroy a language pack.

    solum lp logs <NAME|UUID>
        Show logs for a language pack.
    """

    def create(self):
        """Create a language pack."""
        self.parser.add_argument('--param-file',
                                 dest='paramfile',
                                 help="Local parameter file location")
        self.parser.add_argument('name',
                                 type=ValidLPName,
                                 help="Language pack name.")
        self.parser.add_argument('--name',
                                 type=ValidLPName,
                                 dest='name',
                                 help="Language pack name.")
        self.parser.add_argument('git_url',
                                 help=("Github url of custom "
                                       "language pack repository."))
        self.parser.add_argument('--git_url',
                                 dest='git_url',
                                 help=("Github url of custom "
                                       "language pack repository."))
        self.parser.add_argument('--lp_metadata',
                                 help="Language pack metadata file.")
        self.parser._names['git_url'] = 'repo URL'
        args = self.parser.parse_args()

        param_data = {}
        if args.paramfile is not None:
            try:
                with open(args.paramfile, 'r') as inf:
                    param_data = yamlutils.load(inf.read())
            except Exception as exp:
                raise exc.CommandException(str(exp))

        lp_metadata = None

        if args.lp_metadata:
            with open(args.lp_metadata) as lang_pack_metadata:
                try:
                    lp_metadata = json.dumps(json.load(lang_pack_metadata))
                except ValueError as excp:
                    message = ("Malformed metadata file: %s" % str(excp))
                    raise exc.CommandError(message=message)

        languagepack = {}
        try:
            languagepack = self.client.languagepacks.create(
                name=args.name, source_uri=args.git_url,
                lp_metadata=lp_metadata,
                lp_params=param_data)
        except exceptions.Conflict as conflict:
            message = ("%s" % conflict.message)
            raise exc.CommandError(message=message)

        fields = ['uuid', 'name', 'description', 'status', 'source_uri']
        self._print_dict(languagepack, fields, wrap=72)

    def delete(self):
        """Delete a language pack."""
        self.parser.add_argument('lp_id',
                                 help="Language pack id")
        self.parser._names['lp_id'] = 'languagepack'
        args = self.parser.parse_args()
        self.client.languagepacks.delete(lp_id=args.lp_id)

    def list(self):
        """List all language packs."""
        fields = ['uuid', 'name', 'description', 'status', 'source_uri']
        languagepacks = self.client.languagepacks.list()
        self._print_list(languagepacks, fields)

    def show(self):
        """Get a language pack."""
        self.parser.add_argument('lp_id',
                                 help="Language pack id")
        self.parser._names['lp_id'] = 'languagepack'
        args = self.parser.parse_args()
        languagepack = self.client.languagepacks.find(name_or_id=args.lp_id)
        fields = ['uuid', 'name', 'description', 'status', 'source_uri']
        self._print_dict(languagepack, fields, wrap=72)

    def logs(self):
        """Get language pack Logs."""
        self.parser.add_argument('lp_id',
                                 help="languagepack uuid or name")
        args = self.parser.parse_args()
        loglist = cli_lp.LanguagePackManager(self.client).logs(
            lp_id=str(args.lp_id))

        fields = ["resource_uuid", "created_at"]
        for log in loglist:
            strategy_info = json.loads(log.strategy_info)
            if log.strategy == 'local':
                if 'local_storage' not in fields:
                    fields.append('local_storage')
                log.local_storage = log.location
            elif log.strategy == 'swift':
                if 'swift_container' not in fields:
                    fields.append('swift_container')
                if 'swift_path' not in fields:
                    fields.append('swift_path')
                log.swift_container = strategy_info['container']
                log.swift_path = log.location
            else:
                if 'location' not in fields:
                    fields.append('location')

        self._print_list(loglist, fields)


class AppCommands(cli_utils.CommandsBase):
    """Commands for working with actual applications.

Available commands:
    solum app list
        Print an index of all deployed applications.

    solum app show <NAME|ID>
        Print detailed information about one application.

    solum app create [--app-file <AppFile>] [--git-url <GIT_URL>]
                     [--lp <LANGUAGEPACK>]
                     [--param-file <PARAMFILE>]
                     [--setup-trigger]
                     [--port <PORT>]
                     [--private-repo]
                     [--no-languagepack]
                     [--trigger-workflow <CUSTOM-WORKFLOW>]
                      <CUSTOM-WORKFLOW>=(unittest | build | unittest+build)
                      Without the --trigger-workflow flag,
                      the workflow unittest+build+deploy is triggered
                      (this is the default workflow)

        Register a new application with Solum.

    solum app deploy <NAME|ID> --du-id <du-id>
        Deploy an application, building any applicable artifacts first.
        du-id is optional flag. It can be used to pass in id of a previously
        created deployment unit. If passed, this command will deploy that
        du instead of building one first.

    solum app delete <NAME|ID>
        Delete an application and all related artifacts.

    solum app scale <NAME|ID> <scaling target>

    solum app logs <NAME|UUID> [--wf-id <wf-id>]
        Show the logs of an application for all the workflows.
        wf-id is optional flag which can be used to pass in id of one of
        the existing workflows. If provided, the logs only for that workflow
        are displayed.
    """

    def _validate_app_file(self, app_data):
        if ('workflow_config' in app_data and
                app_data.get('workflow_config') is None):
                msg = "Workflow config cannot be empty"
                raise exc.CommandException(message=msg)
        if ('trigger_actions' in app_data and
                app_data.get('trigger_actions') is None):
                msg = "Trigger actions cannot be empty"
                raise exc.CommandException(message=msg)

        error_message = ("Application name must be 1-100 characters long, "
                         "only contain a-z,0-9,-,_ and start with an alphabet "
                         "character.")

        if app_data.get('name') is not None:
            if not name_is_valid(app_data.get('name')):
                raise exc.CommandError(message=error_message)

        if 'repo_token' not in app_data:
            app_data['repo_token'] = ''

    def _get_and_validate_app_name(self, app_data, args):
        # Check the appfile-supplied name first.
        error_message = ("Application name must be 1-100 characters long, "
                         "only contain a-z,0-9,-,_ and start with an alphabet "
                         "character.")
        app_name = ''
        if args.name:
            app_name = args.name
        elif app_data.get('name') is None:
            while True:
                app_name = six.moves.input("Please name the application.\n> ")
                if name_is_valid(app_name):
                    break
                print(error_message)
        else:
            app_name = app_data.get('name')

        if not name_is_valid(app_name):
            raise exc.CommandError(message=error_message)

        return app_name

    def _get_and_validate_languagepack(self, app_data, args):
        # Check for the language pack. Check args first, then appfile.
        # If it's neither of those places, prompt for it and update the
        # app data.

        if args.no_languagepack:
            app_data['languagepack'] = "False"
            return

        languagepack = None
        if args.languagepack is not None:
            languagepack = args.languagepack
        elif app_data.get('languagepack') is not None:
            languagepack = app_data.get('languagepack')
        # check if given languagepack exists or not
        if languagepack:
            try:
                lp = self.client.languagepacks.find(name_or_id=languagepack)
            except Exception:
                raise exc.CommandError(
                    "Languagepack '%s' not found." % languagepack)
            if lp is None or lp.status != 'READY':
                raise exc.CommandError("No languagepack in READY state. "
                                       "Create a languagepack first.")
            app_data['languagepack'] = languagepack
        else:
            languagepacks = self.client.languagepacks.list()
            filtered_list = cli_utils.filter_ready_lps(languagepacks)

            if len(filtered_list) > 0:
                lpnames = [lang_pack.name for lang_pack in filtered_list]
                lp_uuids = [lang_pack.uuid for lang_pack in filtered_list]
                fields = ['uuid', 'name', 'description',
                          'status', 'source_uri']
                self._print_list(filtered_list, fields)
                languagepack = six.moves.input("Please choose a languagepack "
                                               "from the above list.\n> ")
                while languagepack not in lpnames + lp_uuids:
                    languagepack = six.moves.input("You must choose one of "
                                                   "the named  language "
                                                   "packs.\n> ")
                app_data['languagepack'] = languagepack
            else:
                raise exc.CommandError("No languagepack in READY state. "
                                       "Create a languagepack first.")

    def _get_app_repo_details(self, app_data, args):
        def read_private_sshkey(sshkey_file):
            private_sshkey = ''
            try:
                with open(sshkey_file, 'r') as inf:
                    private_sshkey = inf.read()
            except Exception as exp:
                raise exc.CommandException(str(exp))
            return private_sshkey

        git_rev = 'master'
        git_url = None
        if (app_data.get('source') is not None and
                app_data.get('source').get('repository') is not None):
                    git_url = app_data['source']['repository']
        # Commandline flag overrides stuff in the app-file
        if args.git_url is not None:
            git_url = args.git_url
        # Take input from user
        elif (app_data.get('source') is None or
                app_data['source'].get('repository') is None or
                app_data['source']['repository'] is ''):
            git_url = six.moves.input("Please specify a git repository URL "
                                      "for your application.\n> ")
            git_rev_i = six.moves.input("Please specify revision"
                                        "(default is master).\n> ")
            if git_rev_i is '':
                git_rev = 'master'
            else:
                git_rev = git_rev_i

        assert(git_url is not None)
        assert(git_rev is not None)

        # check if given repo is a private repository
        is_private = (args.private_repo or
                      app_data['source'].get('private', False))

        git_url = transform_git_url(git_url, is_private)

        private_sshkey = app_data['source'].get('private_ssh_key', '')
        if is_private and not private_sshkey:
            sshkey_file = six.moves.input("Please specify private sshkey file "
                                          "full path: ")
            sshkey_file = sshkey_file.strip()
            private_sshkey = read_private_sshkey(sshkey_file)

        if is_private and private_sshkey == '':
            msg = "Must provide private sshkey for private repositories."
            raise exc.CommandError(message=msg)

        git_src = dict()
        git_src['private'] = is_private
        git_src['private_ssh_key'] = private_sshkey
        git_src['repository'] = git_url
        git_src['revision'] = git_rev
        app_data['source'] = git_src

    def _get_run_command(self, app_data, args):
        run_cmd = None

        if args.run_cmd is not None:
            run_cmd = args.run_cmd
        elif (app_data.get('workflow_config') is None or
                app_data['workflow_config'].get('run_cmd') is '' or
                app_data['workflow_config'].get('run_cmd') is None):
            run_cmd = six.moves.input("Please specify start/run command for "
                                      "your application.\n> ")

        if app_data.get('workflow_config') is None:
            run_cmd_dict = dict()
            run_cmd_dict['run_cmd'] = run_cmd
            app_data['workflow_config'] = run_cmd_dict
        elif (app_data['workflow_config'].get('run_cmd') is '' or
              app_data['workflow_config'].get('run_cmd') is None):
            app_data['workflow_config']['run_cmd'] = run_cmd

    def _get_unittest_command(self, app_data, args):
        unittest_cmd = None

        if args.unittest_cmd is not None:
            unittest_cmd = args.unittest_cmd
            if app_data.get('workflow_config') is None:
                unittest_cmd_dict = dict()
                unittest_cmd_dict['test_cmd'] = unittest_cmd
                app_data['workflow_config'] = unittest_cmd_dict
            elif (app_data['workflow_config'].get('test_cmd') is '' or
                  app_data['workflow_config'].get('test_cmd') is None):
                app_data['workflow_config']['test_cmd'] = unittest_cmd

    def _get_port(self, app_data, args):
        port_list = []

        if (app_data.get('ports') is None or
                app_data['ports'] is '' or app_data['ports'] == [None]):
            if args.port:
                port_list.append(int(args.port))
            else:
                print("Using 80 as the app's default listening port")
                port_list.append(int(80))

            app_data['ports'] = port_list

    def _get_parameters(self, app_data, args):
        app_data['parameters'] = {}
        if args.param_file is not None:
            try:
                with open(args.param_file) as param_f:
                    param_def = param_f.read()
                app_data['parameters'] = yamlutils.load(param_def)
            except IOError:
                message = "Could not open param file %s." % args.param_file
                raise exc.CommandError(message=message)
            except ValueError:
                message = ("Param file %s was not YAML." %
                           args.param_file)
                raise exc.CommandError(message=message)

    def _setup_github_trigger(self, app_data, app, args):
        # If a token is supplied, we won't need to generate one.
        provided_token = ''
        obtained_token = ''
        if 'repo_token' in app_data:
            provided_token = app_data['repo_token']

        if args.setup_trigger or args.workflow:
            trigger_uri = vars(app).get('trigger_uri', '')
            if trigger_uri:
                workflow = None
                if args.workflow:
                    workflow = args.workflow.replace('+', ' ').split(' ')
                try:
                    git_url = app_data['source']['repository']

                    gha = github.GitHubAuth(git_url,
                                            repo_token=provided_token)
                    gha.create_webhook(trigger_uri, workflow=workflow)

                    if not provided_token:
                        try:
                            obtained_token = gha.create_repo_token()
                            # Update the app with the generated repo_token
                            to_update = {}
                            to_update['repo_token'] = obtained_token
                            self.client.apps.patch(app_id=app.id, **to_update)
                        except Exception:
                            print("Error in obtaining github token.")
                            return ''

                except github.GitHubException as ghe:
                    raise exc.CommandError(message=str(ghe))

    def create(self):

        parsed, _ = self.parser.parse_known_args()
        config.username = parsed.os_username
        config.password = parsed.os_password
        config.tenant = parsed.os_tenant_name

        self.register()

    def register(self):
        """Register a new app."""
        self.parser.add_argument('--app-file',
                                 dest='appfile',
                                 help="Local appfile location")
        self.parser.add_argument('--name',
                                 dest='name',
                                 type=ValidName,
                                 help="Application name")
        self.parser.add_argument('--languagepack',
                                 help='Language pack')
        self.parser.add_argument('--lp',
                                 dest='languagepack',
                                 help='Language pack')
        self.parser.add_argument('--git-url',
                                 dest='git_url',
                                 help='Source repo')
        self.parser.add_argument('--run-cmd',
                                 dest='run_cmd',
                                 help="Application entry point")
        self.parser.add_argument('--unittest-cmd',
                                 dest='unittest_cmd',
                                 help="Command to execute unit tests")
        self.parser.add_argument('--port',
                                 dest="port",
                                 type=ValidPort,
                                 help="The port your application listens on")
        self.parser.add_argument('--param-file',
                                 dest='param_file',
                                 help="A yaml file containing custom"
                                      " parameters to be used in the"
                                      " application")
        self.parser.add_argument('--setup-trigger',
                                 action='store_true',
                                 dest='setup_trigger',
                                 help="Set up app trigger on git repo")
        self.parser.add_argument('--no-languagepack',
                                 action='store_true',
                                 dest='no_languagepack',
                                 help="Flag to register an app without"
                                      " a languagepack")
        self.parser.add_argument('--private-repo',
                                 action='store_true',
                                 dest='private_repo',
                                 help="Source repo requires authentication.")

        trigger_help = ("Which of stages build, unittest, deploy to trigger "
                        "from git. For example: "
                        "--trigger-workflow=unittest+build+deploy. "
                        "Implies --setup-trigger.")
        self.parser.add_argument('--trigger-workflow',
                                 default='',
                                 dest='workflow',
                                 help=trigger_help)

        args = self.parser.parse_args()
        app_data = None
        if args.appfile is not None:
            try:
                with open(args.appfile, 'r') as inf:
                    app_data = yamlutils.load(inf.read())
                    self._validate_app_file(app_data)
            except Exception as exp:
                raise exc.CommandException(str(exp))
        else:
            app_data = {
                'version': 1,
                'description': 'default app description.',
                'source': {
                    'repository': '',
                    'revision': 'master',
                    'private': False,
                    'private_ssh_key': '',
                    'repo_token': ''
                },
                'workflow_config': {
                    'test_cmd': '',
                    'run_cmd': ''
                },
                'trigger_actions': ['build', 'deploy'],
            }

        app_name = self._get_and_validate_app_name(app_data, args)
        app_data['name'] = app_name

        self._get_and_validate_languagepack(app_data, args)

        self._get_app_repo_details(app_data, args)

        self._get_run_command(app_data, args)

        self._get_unittest_command(app_data, args)

        self._get_port(app_data, args)

        self._get_parameters(app_data, args)

        self._validate_app_data(app_data)

        if args.workflow:
            app_data['trigger_actions'] = (
                args.workflow.replace('+', ' ').split(' '))

        app = self.client.apps.create(**app_data)

        self._setup_github_trigger(app_data, app, args)

        app.trigger = app.trigger_actions
        app.workflow = app.workflow_config

        fields = ['name', 'id', 'created_at', 'description', 'languagepack',
                  'ports', 'source', 'workflow',
                  'trigger_uuid', 'trigger', 'trigger_uri']
        self._print_dict(app, fields, wrap=72)

    def _validate_app_data(self, app_data):
        # app file schema
        schema = {
            "title": "app file schema",
            "type": "object",
            "properties": {
                "version": {
                    "type": "integer"
                },
                "name": {
                    "type": "string"
                },
                "description": {
                    "type": "string"
                },
                "languagepack": {
                    "type": "string"
                },
                "source": {
                    "type": "object",
                    "properties": {
                        "repository": {
                            "type": "string"
                        },
                        "revision": {
                            "type": "string"
                        },
                        "private": {
                            "type": "boolean"
                        },
                        "repo_token": {
                            "type": "string"
                        },
                        "private_ssh_key": {
                            "type": "string"
                        }
                    }
                },
                "trigger_actions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["unittest", "build", "deploy"]
                    }
                },
                "workflow_config": {
                    "type": "object",
                    "properties": {
                        "test_cmd": {
                            "type": "string"
                        },
                        "run_cmd": {
                            "type": "string"
                        }
                    }
                },
                "ports": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "parameters": {
                    "type": "object"
                }
            },
            "required": [
                "version",
                "name",
                "description",
                "languagepack",
                "source",
                "trigger_actions",
                "workflow_config",
                "ports"
            ]
        }
        try:
            jsonschema.validate(app_data, schema)
        except jsonschema.exceptions.ValidationError as exp:
            raise exc.CommandError(message=str(exp))

    def update(self):
        """Update the registration of an existing app."""
        self.parser.add_argument('app')

        self.parser.add_argument('--name', type=str)
        self.parser.add_argument('--desc', type=str)
        self.parser.add_argument('--lp', type=str)
        self.parser.add_argument('--ports', type=str)
        self.parser.add_argument('--source.repo', dest='source_repo', type=str)
        self.parser.add_argument('--source.rev', dest='source_rev', type=str)
        self.parser.add_argument('--test_cmd', type=str)
        self.parser.add_argument('--run_cmd', type=str)
        self.parser.add_argument('--trigger', type=str)

        args = self.parser.parse_args()

        app = self.client.apps.find(name_or_id=args.app)

        to_update = {}
        if args.name:
            to_update['name'] = args.name
        if args.desc:
            to_update['description'] = args.desc
        if args.lp:
            to_update['languagepack'] = args.lp
        if args.ports:
            ports = args.ports.strip('[]').replace(',', ' ')
            ports = [int(p, 10) for p in ports.split(' ') if p]
            to_update['ports'] = ports
        if args.source_repo:
            to_update['source'] = to_update.get('source', {})
            to_update['source']['repository'] = args.source_repo
        if args.source_rev:
            to_update['source'] = to_update.get('source', {})
            to_update['source']['revision'] = args.source_rev
        if args.test_cmd:
            to_update['workflow_config'] = to_update.get('trigger', {})
            to_update['workflow_config']['test_cmd'] = args.test_cmd
        if args.run_cmd:
            to_update['workflow_config'] = to_update.get('trigger', {})
            to_update['workflow_config']['run_cmd'] = args.run_cmd
        if args.trigger:
            trigger = args.trigger.strip('[]').replace(',', ' ').split(' ')
            to_update['trigger_actions'] = trigger

        if not to_update:
            raise exc.CommandException(message="Nothing to update")

        updated_app = self.client.apps.patch(app_id=app.id, **to_update)

        updated_app.trigger = updated_app.trigger_actions
        updated_app.workflow = updated_app.workflow_config

        fields = ['name', 'id', 'created_at', 'description', 'languagepack',
                  'entry_points', 'ports', 'source', 'workflow',
                  'trigger_uuid', 'trigger']
        self._print_dict(updated_app, fields, wrap=72)

    def list(self):
        """List all apps."""
        apps = self.client.apps.list()
        fields = ['name', 'id', 'created_at', 'description', 'languagepack']
        self._print_list(apps, fields)

    def show(self):
        """Show details of one app."""
        self.parser.add_argument('name')
        args = self.parser.parse_args()
        app = self.client.apps.find(name_or_id=args.name)

        fields = ['name', 'id', 'created_at', 'updated_at', 'description',
                  'languagepack', 'entry_points', 'ports', 'source',
                  'trigger_uuid', 'trigger', 'app_url']

        app.trigger = app.trigger_actions
        app.workflow = app.workflow_config
        if app.scale_config:
            if app.scale_config[app.name]['target']:
                app.target_instances = app.scale_config[app.name]['target']
                fields.append('target_instances')

        self._print_dict(app, fields, wrap=72)

        wfman = cli_wf.WorkflowManager(self.client, app_id=app.id)
        wfs = wfman.list()
        fields = ['wf_id', 'id', 'status']
        print("'%s' workflows and their status:" % args.name)
        self._print_list(wfs, fields)

    def delete(self):
        """Delete an app."""
        self.parser.add_argument('name')
        args = self.parser.parse_args()
        app = self.client.apps.find(name_or_id=args.name)
        cli_app.AppManager(self.client).delete(
            app_id=str(app.id))

    def _create_scaling_workflow(self, actions, app_name_id, tgt):
        app = self.client.apps.find(name_or_id=app_name_id)
        wf = (cli_wf.WorkflowManager(self.client,
                                     app_id=app.id).create(actions=actions,
                                                           scale_target=tgt))
        fields = ['wf_id', 'app_id', 'actions', 'config',
                  'source', 'id', 'created_at', 'updated_at']
        self._print_dict(wf, fields, wrap=72)

    def _create_workflow(self, actions, app_name_id=''):
        if not app_name_id:
            app = self.client.apps.find(name_or_id=app_name_id)
        else:
            self.parser.add_argument('name')
            args = self.parser.parse_args()
            app = self.client.apps.find(name_or_id=args.name)
        wf = (cli_wf.WorkflowManager(self.client,
                                     app_id=app.id).create(actions=actions))
        fields = ['wf_id', 'app_id', 'actions', 'config',
                  'source', 'id', 'created_at', 'updated_at']
        self._print_dict(wf, fields, wrap=72)

    def _create_workflow_for_prebuilt_du(self, actions, app_name_id, du_id):
        app = self.client.apps.find(name_or_id=app_name_id)
        wf = (cli_wf.WorkflowManager(self.client,
                                     app_id=app.id).create(actions=actions,
                                                           du_id=du_id))
        fields = ['wf_id', 'app_id', 'actions', 'config',
                  'source', 'id', 'created_at', 'updated_at']
        self._print_dict(wf, fields, wrap=72)

    def unittest(self):
        """Create a new workflow for an app."""
        actions = ['unittest']
        self._create_workflow(actions)

    def build(self):
        """Create a new workflow for an app."""
        actions = ['unittest', 'build']
        self._create_workflow(actions)

    def deploy(self):
        """Create a new workflow for an app."""
        self.parser.add_argument("name")
        self.parser.add_argument('--du-id',
                                 dest="du_id",
                                 help="ID of the DU image.")
        args = self.parser.parse_args()
        if args.du_id:
            actions = ['deploy']
            self._create_workflow_for_prebuilt_du(actions, args.name,
                                                  args.du_id)
        else:
            actions = ['unittest', 'build', 'deploy']
            self._create_workflow(actions, args.name)

    def scale(self):
        """Scale the app."""
        self.parser.add_argument('name')
        self.parser.add_argument('target')
        args = self.parser.parse_args()

        target = args.target
        try:
            target = int(target)
        except ValueError:
            msg = "Must provide integer value for scale target."
            raise exc.CommandException(message=msg)

        if target <= 0:
            msg = "Scale target must be greater than zero."
            raise exc.CommandException(message=msg)

        actions = ['scale']
        self._create_scaling_workflow(actions, args.name, target)

    def _display_logs_for_all_workflows(self, app):
        wfman = cli_wf.WorkflowManager(self.client, app_id=app.id)
        wfs = wfman.list()

        all_logs_list = []
        fields = ["resource_uuid", "created_at"]
        for wf in wfs:
            revision = wf.wf_id
            loglist = wfman.logs(revision_or_id=revision)
            for log in loglist:
                all_logs_list.append(log)
                strategy_info = json.loads(log.strategy_info)
                if log.strategy == 'local':
                    if 'local_storage' not in fields:
                        fields.append('local_storage')
                    log.local_storage = log.location
                elif log.strategy == 'swift':
                    if 'swift_container' not in fields:
                        fields.append('swift_container')
                    if 'swift_path' not in fields:
                        fields.append('swift_path')
                    log.swift_container = strategy_info['container']
                    log.swift_path = log.location
                else:
                    if 'location' not in fields:
                        fields.append('location')
        self._print_list(all_logs_list, fields)

    def logs(self):
        """Print a list of all logs belonging to a single app."""

        self.parser.add_argument('name')

        self.parser.add_argument('--wf-id',
                                 dest='wf_id',
                                 help="Workflow ID")

        args = self.parser.parse_args()
        app = self.client.apps.find(name_or_id=args.name)

        if args.wf_id:
            try:
                revision = int(args.wf_id, 10)
            except (ValueError, TypeError):
                revision = args.wf_id
            display_logs_for_single_workflow(self, app, revision)
        else:
            self._display_logs_for_all_workflows(app)


def display_logs_for_single_workflow(ref, app, revision):
    wfman = cli_wf.WorkflowManager(ref.client, app_id=app.id)
    loglist = wfman.logs(revision_or_id=revision)
    fields = ["resource_uuid", "created_at"]
    for log in loglist:
        strategy_info = json.loads(log.strategy_info)
        if log.strategy == 'local':
            if 'local_storage' not in fields:
                fields.append('local_storage')
            log.local_storage = log.location
        elif log.strategy == 'swift':
            if 'swift_container' not in fields:
                fields.append('swift_container')
            if 'swift_path' not in fields:
                fields.append('swift_path')
            log.swift_container = strategy_info['container']
            log.swift_path = log.location
        else:
            if 'location' not in fields:
                fields.append('location')

    ref._print_list(loglist, fields)


class WorkflowCommands(cli_utils.CommandsBase):
    """Commands for working with workflows.

Available commands:

    solum workflow list <APP_NAME|UUID>
        List all application workflows.

    solum workflow show <APP_NAME|UUID> <WORKFLOW_ID|UUID>
        Print the details of a workflow.

    solum workflow logs <APP_NAME|UUID> <WORKFLOW_ID|UUID>
        List all the logs of a given workflow.
    """

    def list(self):
        """Show all of an app's live workflows."""
        self.parser.add_argument('app')
        args = self.parser.parse_args()
        app = self.client.apps.find(name_or_id=args.app)
        wfs = cli_wf.WorkflowManager(self.client, app_id=app.id).list()
        fields = ['wf_id', 'id', 'actions', 'status',
                  'created_at', 'updated_at']
        self._print_list(wfs, fields)

    def show(self):
        """Show one of an app's live workflows."""
        # Either "solum workflow show <app_id_or_name> <workflow_uuid>
        # Or "solum workflow show <app_id_or_name> <workflow_revision>
        self.parser.add_argument('app')
        self.parser.add_argument('workflow')
        args = self.parser.parse_args()
        revision = args.workflow
        try:
            revision = int(revision, 10)
        except ValueError:
            revision = args.workflow
        app = self.client.apps.find(name_or_id=args.app)

        wfman = cli_wf.WorkflowManager(self.client, app_id=app.id)
        wf = wfman.find(revision_or_id=revision)
        fields = ['wf_id', 'app_id', 'actions', 'config',
                  'source', 'id', 'created_at', 'updated_at', 'status']
        self._print_dict(wf, fields, wrap=72)

    def logs(self):
        """Show one of an app's live workflows logs."""
        self.parser.add_argument('app',
                                 help="App uuid or name")
        self.parser.add_argument('workflow',
                                 help="Workflow id or uuid")
        args = self.parser.parse_args()
        revision = args.workflow
        try:
            revision = int(revision, 10)
        except ValueError:
            revision = args.workflow
        app = self.client.apps.find(name_or_id=args.app)
        display_logs_for_single_workflow(self, app, revision)


class OldAppCommands(cli_utils.CommandsBase):
    """Commands for working with applications.

Available commands:
    solum app list
        Print an index of all deployed applications.

    solum app show <NAME|UUID>
        Print detailed information about one application.

    solum app create [--plan-file <PLANFILE>] [--git-url <GIT_URL>]
                     [--lp <LANGUAGEPACK>] [--run-cmd <RUN_CMD>]
                     [--unittest-cmd <UNITTEST_CMD>]
                     [--name <NAME>] [--port <PORT>]
                     [--param-file <PARAMFILE>]
                     [--desc <DESCRIPTION>]
                     [--setup-trigger]
                     [--private-repo]
                     [--trigger-workflow <WORKFLOW>]
        Register a new application with Solum.

    solum app deploy <NAME|UUID>
        Deploy an application, building any applicable artifacts first.

    solum app logs <NAME|UUID>
        Show the logs of an application for all the deployments.

    solum app delete <NAME|UUID>
        Delete an application and all related artifacts.
"""

    def _get_assemblies_by_plan(self, plan):
        # TODO(datsun180b): Write this.
        return []

    def _validate_plan_file(self, plan_definition):
        if 'artifacts' not in plan_definition:
            raise exc.CommandException(message="Missing artifacts section")
        elif plan_definition['artifacts'] is None:
            raise exc.CommandException(message="Artifacts cannot be empty")
        elif 'content' not in plan_definition['artifacts'][0]:
            raise exc.CommandException(message="Artifact content missing")

        error_message = ("Application name must be 1-100 characters long, "
                         "only contain a-z,0-9,-,_ and start with an alphabet "
                         "character.")

        if plan_definition.get('name') is not None:
            if not name_is_valid(plan_definition.get('name')):
                raise exc.CommandError(message=error_message)

    def list(self):
        """Print a list of all deployed applications."""
        # This is just "plan list".
        # TODO(datsun180b): List each plan and its associated
        # assemblies.
        fields = ['uuid', 'name', 'description']
        plans = self.client.plans.list()
        self._print_list(plans, fields)

    def show(self):
        """Print detailed information about one application."""
        # This is just "plan show <PLAN>".
        # TODO(datsun180b): List the details of the plan, and
        # also the current build state, build number, and running
        # assembly status. We don't have all the pieces for that yet.
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args = self.parser.parse_args()
        try:
            plan = self.client.plans.find(name_or_id=args.app)
        except exceptions.NotFound:
            message = "No app named '%s'." % args.app
            raise exceptions.NotFound(message=message)

        # Fetch the most recent app_uri.
        assemblies = self.client.assemblies.list()
        app_uri = ''
        updated = ''
        app_status = 'REGISTERED'
        for a in assemblies:
            plan_uuid = a.plan_uri.split('/')[-1]
            if plan_uuid != plan.uuid:
                continue
            if a.updated_at >= updated:
                updated = a.updated_at
                app_uri = a.application_uri
                app_status = a.status

        plan.application_uri = app_uri
        plan.status = app_status
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts',
                  'trigger_uri', 'application_uri', 'status']
        self._print_dict(plan, fields, wrap=72)
        artifacts = copy.deepcopy(vars(plan).get('artifacts'))
        show_public_keys(artifacts)

    def create(self):
        """Register a new application with Solum."""
        # This is just "plan create" with a little proactive
        # parsing of the planfile.

        self.parser.add_argument('--plan-file',
                                 dest='planfile',
                                 help="Local planfile location")
        self.parser.add_argument('--git-url',
                                 help='Source repo')
        self.parser.add_argument('--languagepack',
                                 help='Language pack')
        self.parser.add_argument('--lp',
                                 dest='languagepack',
                                 help='Language pack')
        self.parser.add_argument('--run-cmd',
                                 help="Application entry point")
        self.parser.add_argument('--unittest-cmd',
                                 help="Command to execute unit tests")
        self.parser.add_argument('--port',
                                 type=ValidPort,
                                 help="The port your application listens on")
        self.parser.add_argument('--name',
                                 type=ValidName,
                                 help="Application name")
        self.parser.add_argument('--desc',
                                 help="Application description")
        self.parser.add_argument('--param-file',
                                 dest='param_file',
                                 help="A yaml file containing custom"
                                      " parameters to be used in the"
                                      " application")
        self.parser.add_argument('--setup-trigger',
                                 action='store_true',
                                 dest='setup_trigger',
                                 help="Set up app trigger on git repo")
        self.parser.add_argument('--private-repo',
                                 action='store_true',
                                 dest='private_repo',
                                 help="Source repo requires authentication.")

        trigger_help = ("Which of stages build, unittest, deploy to trigger "
                        "from git. For example: "
                        "--trigger-workflow=unittest+build+deploy. "
                        "Implies --setup-trigger.")
        self.parser.add_argument('--trigger-workflow',
                                 default='',
                                 dest='workflow',
                                 help=trigger_help)

        args = self.parser.parse_args()

        # Get the plan file. Either get it from args, or supply
        # a skeleton.
        plan_definition = None
        if args.planfile is not None:
            planfile = args.planfile
            try:
                with open(planfile) as definition_file:
                    definition = definition_file.read()
                    plan_definition = yamlutils.load(definition)
                    self._validate_plan_file(plan_definition)
                    if (plan_definition['artifacts'][0].get('language_pack')
                            is not None):
                        lp = plan_definition['artifacts'][0]['language_pack']
                        if lp != 'auto':
                            try:
                                lp1 = (
                                    self.client.languagepacks.find
                                    (name_or_id=lp)
                                )
                            except Exception as e:
                                if type(e).__name__ == 'NotFound':
                                    raise exc.CommandError("Languagepack %s "
                                                           "not registered"
                                                           % lp)
                            filtered_list = cli_utils.filter_ready_lps([lp1])
                            if len(filtered_list) <= 0:
                                raise exc.CommandError("Languagepack %s "
                                                       "not READY" % lp)
                    if plan_definition['artifacts'][0].get('ports') is None:
                        print("No application port specified in plan file.")
                        print("Defaulting to port 80.")
                        plan_definition['artifacts'][0]['ports'] = 80
            except IOError:
                message = "Could not open plan file %s." % planfile
                raise exc.CommandError(message=message)
            except ValueError:
                message = ("Plan file %s was not a valid YAML mapping." %
                           planfile)
                raise exc.CommandError(message=message)
        else:
            plan_definition = {
                'version': 1,
                'artifacts': [{
                    'artifact_type': 'heroku',
                    'name': '',
                    'content': {},
                }]}

        # NOTE: This assumes the plan contains exactly one artifact.

        # Check the planfile-supplied name first.
        error_message = ("Application name must be 1-100 characters long, "
                         "only contain a-z,0-9,-,_ and start with an alphabet "
                         "character.")
        app_name = ''
        if plan_definition.get('name') is not None:
            if not name_is_valid(plan_definition.get('name')):
                raise exc.CommandError(message=error_message)
            app_name = plan_definition.get('name')
        # Check the arguments next.
        elif args.name:
            if name_is_valid(args.name):
                app_name = args.name
        # Just ask.
        else:
            while True:
                app_name = six.moves.input("Please name the application.\n> ")
                if name_is_valid(app_name):
                    break
                print(error_message)

        plan_definition['name'] = app_name

        # Check for the language pack. Check args first, then planfile.
        # If it's neither of those places, prompt for it and update the
        # plan definition.

        languagepack = None
        if args.languagepack is not None:
            languagepack = args.languagepack
            plan_definition['artifacts'][0]['language_pack'] = languagepack
        elif plan_definition['artifacts'][0].get('language_pack') is None:
            languagepacks = self.client.languagepacks.list()
            filtered_list = cli_utils.filter_ready_lps(languagepacks)

            if len(filtered_list) > 0:
                lpnames = [lang_pack.name for lang_pack in filtered_list]
                lp_uuids = [lang_pack.uuid for lang_pack in filtered_list]
                fields = ['uuid', 'name', 'description',
                          'status', 'source_uri']
                self._print_list(filtered_list, fields)
                languagepack = six.moves.input("Please choose a languagepack "
                                               "from the above list.\n> ")
                while languagepack not in lpnames + lp_uuids:
                    languagepack = six.moves.input("You must choose one of "
                                                   "the named language "
                                                   "packs.\n> ")
                plan_definition['artifacts'][0]['language_pack'] = languagepack
            else:
                raise exc.CommandError("No languagepack in READY state. "
                                       "Create a languagepack first.")

        # Check for the git repo URL. Check args first, then the planfile.
        # If it's neither of those places, prompt for it and update the
        # plan definition.

        git_url = None
        if args.git_url is not None:
            plan_definition['artifacts'][0]['content']['href'] = args.git_url
        if plan_definition['artifacts'][0]['content'].get('href') is None:
            git_url = six.moves.input("Please specify a git repository URL "
                                      "for your application.\n> ")
            plan_definition['artifacts'][0]['content']['href'] = git_url
        git_url = plan_definition['artifacts'][0]['content']['href']

        # If a token is supplied, we won't need to generate one.
        artifact = plan_definition['artifacts'][0]
        repo_token = artifact.get('repo_token')

        is_private = (args.private_repo or
                      artifact['content'].get('private'))
        plan_definition['artifacts'][0]['content']['private'] = is_private

        git_url = transform_git_url(git_url, is_private)
        plan_definition['artifacts'][0]['content']['href'] = git_url

        # If we'll be adding a trigger, or the repo is private,
        # we'll need to use a personal access token.
        # The GitHubAuth object will create one if repo_token is null.
        if is_private or args.setup_trigger or args.workflow:
            gha = github.GitHubAuth(git_url, repo_token=repo_token)
            repo_token = repo_token or gha.repo_token
            # Created or provided, the repo token needs to be in the
            # plan data before we call client.plans.create.
            plan_definition['artifacts'][0]['repo_token'] = repo_token

        # Check for the entry point. Check args first, then the planfile.
        # If it's neither of those places, prompt for it and update the
        # plan definition.
        run_cmd = None
        if args.run_cmd is not None:
            plan_definition['artifacts'][0]['run_cmd'] = args.run_cmd
        if plan_definition['artifacts'][0].get('run_cmd') is None:
            run_cmd = six.moves.input("Please specify start/run command for "
                                      "your application.\n> ")
            plan_definition['artifacts'][0]['run_cmd'] = run_cmd

        # Check for unit test command
        if args.unittest_cmd is not None:
            plan_definition['artifacts'][0]['unittest_cmd'] = args.unittest_cmd

        # Check for the port.
        if args.port is not None:
            plan_definition['artifacts'][0]['ports'] = int(args.port)
        if plan_definition['artifacts'][0].get('ports') is None:
            plan_definition['artifacts'][0]['ports'] = 80

        # Update name and description if specified.
        a_name = ''
        if (plan_definition['artifacts'][0].get('name') is not None
                and plan_definition['artifacts'][0]['name'] is not ''):
            a_name = plan_definition['artifacts'][0]['name']
            a_name = a_name.lower()
        else:
            a_name = app_name.lower()
        if not lpname_is_valid(a_name):
            # https://github.com/docker/compose/issues/941
            # Docker build only allows lowercase names for now.
            msg = name_error_message("Artifact names")
            raise exc.CommandError(msg)
        plan_definition['artifacts'][0]['name'] = a_name

        if args.desc is not None:
            plan_definition['description'] = args.desc
        elif plan_definition.get('description') is None:
            plan_definition['description'] = ''

        if args.param_file is not None:
            try:
                with open(args.param_file) as param_f:
                    param_def = param_f.read()
                plan_definition['parameters'] = yamlutils.load(param_def)
            except IOError:
                message = "Could not open param file %s." % args.param_file
                raise exc.CommandError(message=message)
            except ValueError:
                message = ("Param file %s was not YAML." %
                           args.param_file)
                raise exc.CommandError(message=message)

        plan = self.client.plans.create(yamlutils.dump(plan_definition))
        plan.status = 'REGISTERED'
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts',
                  'trigger_uri', 'status']

        artifacts = copy.deepcopy(vars(plan).get('artifacts'))
        self._print_dict(plan, fields, wrap=72)

        # Solum generated a keypair; only upload the public key if we already
        # have a repo_token, since we'd only have one if we've authed against
        # github already.
        content = vars(artifacts[0]).get('content')
        if content:
            public_key = content.get('public_key', '')
            if repo_token and is_private and public_key:
                try:
                    gha = github.GitHubAuth(git_url, repo_token=repo_token)
                    gha.add_ssh_key(public_key=public_key)
                except github.GitHubException as ghe:
                    raise exc.CommandError(message=str(ghe))

        if args.setup_trigger or args.workflow:
            trigger_uri = vars(plan).get('trigger_uri', '')
            if trigger_uri:
                workflow = None
                if args.workflow:
                    workflow = args.workflow.replace('+', ' ').split(' ')
                try:
                    gha = github.GitHubAuth(git_url, repo_token=repo_token)
                    gha.create_webhook(trigger_uri, workflow=workflow)
                except github.GitHubException as ghe:
                    raise exc.CommandError(message=str(ghe))

    def deploy(self):
        """Deploy an application, building any applicable artifacts first."""
        # This is just "assembly create" with a little bit of introspection.
        # TODO(datsun180b): Add build() method, and add --build-id argument
        # to this method to allow for build-only and deploy-only workflows.
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args = self.parser.parse_args()
        try:
            plan = self.client.plans.find(name_or_id=args.app)
        except exceptions.NotFound:
            message = "No app named '%s'." % args.app
            raise exceptions.NotFound(message=message)

        assembly = self.client.assemblies.create(name=plan.name,
                                                 description=plan.description,
                                                 plan_uri=plan.uri)
        fields = ['uuid', 'name', 'status', 'application_uri']
        self._print_dict(assembly, fields, wrap=72)

    def delete(self):
        """Delete an application and all related artifacts."""
        # This is "assembly delete" followed by "plan delete".
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args = self.parser.parse_args()
        try:
            plan = self.client.plans.find(name_or_id=args.app)
        except exceptions.NotFound:
            message = "No app named '%s'." % args.app
            raise exceptions.NotFound(message=message)
        cli_plan.PlanManager(self.client).delete(plan_id=str(plan.uuid))


class InfoCommands(cli_utils.NoSubCommands):
    """Show Solum server connection information.

Available commands:

    solum info
        Show Solum endpoint and API release version.

    """

    def info(self):
        parsed, _ = self.parser.parse_known_args()

        # Use the api_endpoint to get the catalog

        ks_kwargs = {
            'username': parsed.os_username,
            'password': parsed.os_password,
            'tenant_name': parsed.os_tenant_name,
            'auth_url': parsed.os_auth_url,
        }

        solum_api_endpoint = parsed.solum_url
        if not solum_api_endpoint:
            ksclient = keystoneclient.Client(**ks_kwargs)
            services = ksclient.auth_ref.service_catalog
            services = services.catalog['serviceCatalog']
            solum_service = [s for s in services if s['name'] == 'solum']
            try:
                endpoint = solum_service[0]['endpoints']
                solum_api_endpoint = endpoint[0]['publicURL']
            except (IndexError, KeyError):
                print("Error: SOLUM_URL not set, and no Solum endpoint "
                      "could be found in service catalog.")

        solum_api_version = ''
        if solum_api_endpoint:
            kwargs = {"disable_ssl_certificate_validation": not self.verify}
            try:
                resp, content = httplib2.Http(**kwargs).request(
                    solum_api_endpoint, 'GET')
                solum_api_version = resp.get('x-solum-release', '')
            except Exception:
                print("Error: Solum endpoint could not be contacted;"
                      " API version could not be determined.")

        print("python-solumclient version %s" % solumclient.__version__)
        print("solum API endpoint: %s" % solum_api_endpoint)
        print("solum API version: %s" % solum_api_version)
        print("solum auth endpoint: %s" % parsed.os_auth_url)
        print("solum auth username: %s" % parsed.os_username)
        print("solum auth tenant/project: %s" % parsed.os_tenant_name)


class PermissiveParser(argparse.ArgumentParser):
    """An ArgumentParser that handles errors without exiting.

    An argparse.ArgumentParser that doesn't sys.exit(2) when it
    gets the wrong number of arguments. Gives us better control
    over exception handling.

    """

    # Used in _check_positional_arguments to give a clearer name to missing
    # positional arguments.
    _names = None

    def __init__(self, *args, **kwargs):
        self._names = {}
        kwargs['add_help'] = False
        kwargs['description'] = argparse.SUPPRESS
        kwargs['usage'] = argparse.SUPPRESS
        super(PermissiveParser, self).__init__(*args, **kwargs)

    def error(self, message):
        raise exc.CommandError(message=message)

    def _report_missing_args(self):
        pass

    def parse_args(self, *args, **kwargs):
        ns, rem = self.parse_known_args(*args, **kwargs)
        if rem:
            unrec = ', '.join([a.split('=')[0].lstrip('-') for a in rem])
            raise exc.CommandError("Unrecognized arguments: %s" % unrec)
        return ns

    def parse_known_args(self, *args, **kwargs):
        ns, rem = argparse.Namespace(), []
        try:
            kwargs['namespace'] = ns
            ns, rem = super(PermissiveParser, self).parse_known_args(
                *args, **kwargs)
        except exc.CommandError:
            pass
        self._check_positional_arguments(ns)
        return ns, rem

    def _check_positional_arguments(self, namespace):
        for argument in self._positionals._group_actions:
            argname = argument.dest
            localname = self._names.get(argname, argname)
            article = 'an' if localname[0] in 'AEIOUaeiou' else 'a'
            if not vars(namespace).get(argname):
                message = 'You must specify %(article)s %(localname)s.'
                message %= {'article': article, 'localname': localname}
                raise exc.CommandError(message=message)


def main():
    """Solum command-line client.

Available commands:

    solum help
        Show this help message.

    solum info
        Show Solum endpoint and API release version.

    solum --version
        Show current Solum client version and exit.

    solum lp help
        Show a help message specific to languagepack commands.

    solum lp create <NAME> <GIT_REPO_URL>
        Create a new language pack from a git repo.

    solum lp list
        Print and index of all available language packs.

    solum lp show <NAME|UUID>
        Print the details of a language pack.

    solum lp delete <NAME|UUID>
        Destroy a language pack.

    solum lp logs <NAME|UUID>
        Show logs for a language pack.

    solum app help
        Show a help message specific to app commands.

    solum app list
        Print an index of all deployed applications.

    solum app show <NAME|UUID>
        Print detailed information about one application.

    solum app create [--app-file <AppFile>] [--git-url <GIT_URL>]
                     [--lp <LANGUAGEPACK>]
                     [--param-file <PARAMFILE>]
                     [--setup-trigger]
                     [--trigger-workflow <CUSTOM-WORKFLOW>]
                      <CUSTOM-WORKFLOW>=(unittest | build | unittest+build)
                      Without the --trigger-workflow flag,
                      the workflow unittest+build+deploy is triggered
                      (this is the default workflow)

        Register a new application with Solum.

    solum app deploy <NAME|UUID>
        Deploy an application, building any applicable artifacts first.
        du-id is optional flag. It can be used to pass in id of a previously
        created deployment unit. If passed, this command will deploy the du
        referenced by the provided du-id instead of building one first.

    solum app delete <NAME|UUID>
        Delete an application and all related artifacts.

    solum app logs <NAME|UUID> [--wf-id <wf-id>]
        Show the logs of an application for all the workflows.
        wf-id is optional flag which can be used to pass in id of one of
        the existing workflows. If provided, the logs only for that workflow
        are displayed.

    solum app scale <APP_NAME|UUID> <target>

    solum workflow list <APP_NAME|UUID>
        List all application workflows.

    solum workflow show <APP_NAME|UUID> <WORKFLOW_ID|UUID>
        Print the details of a workflow.

    solum workflow logs <APP_NAME|UUID> <WORKFLOW_ID|UUID>
        List all the logs of a given workflow.


    SOON TO BE DEPRECATED:

    solum oldapp create [--plan-file <PLANFILE>] [--git-url <GIT_URL>]
                     [--lp <LANGUAGEPACK>] [--run-cmd <RUN_CMD>]
                     [--unittest-cmd <UNITTEST_CMD>]
                     [--name <NAME>] [--port <PORT>]
                     [--param-file <PARAMFILE>]
                     [--desc <DESCRIPTION>]
                     [--setup-trigger]
                     [--private-repo]
                     [--trigger-workflow <WORKFLOW>]
        Register a new application with Solum.

    """

    parser = PermissiveParser()

    resources = {
        'oldapp': OldAppCommands,
        'app': AppCommands,
        'plan': PlanCommands,
        'pipeline': PipelineCommands,
        'lp': LanguagePackCommands,
        'languagepack': LanguagePackCommands,
        'component': ComponentCommands,
        'info': InfoCommands,
        'wf': WorkflowCommands,
        'workflow': WorkflowCommands,
    }

    choices = resources.keys()

    parser.add_argument('resource', choices=choices,
                        default='help',
                        help="Target noun to act upon")

    parser.add_argument('-V', '--version', action='store_true',
                        dest='show_version',
                        help="Report solum version.")

    parser.add_argument('-E', '--show-errors', dest='show_errors',
                        action='store_true',
                        help='Debug. Show traceback on error.')

    parsed, _ = parser.parse_known_args()

    if parsed.show_version:
        print("python-solumclient version %s" % solumclient.__version__)
        return

    resource = vars(parsed).get('resource')

    if resource in resources:
        if parsed.show_errors:
            resources[resource](parser)
        else:
            try:
                resources[resource](parser)
            except Exception as e:
                if hasattr(e, 'message'):
                    print("ERROR: %s" % e.message)
                else:
                    print("ERROR: %s" % e)

    else:
        print(main.__doc__)

if __name__ == '__main__':
    sys.exit(main())
