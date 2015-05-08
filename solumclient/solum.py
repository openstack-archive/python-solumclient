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
* assembly create assembly_name plan_name
* assembly delete assembly_name
* assembly list
* assembly show assembly_id
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
from keystoneclient.v2_0 import client as keystoneclient

import solumclient
from solumclient.common import cli_utils
from solumclient.common import exc
from solumclient.common import github
from solumclient.common import yamlutils
from solumclient.openstack.common.apiclient import exceptions
from solumclient.v1 import assembly as cli_assem
from solumclient.v1 import languagepack as cli_lp
from solumclient.v1 import pipeline as cli_pipe
from solumclient.v1 import plan as cli_plan


def name_is_valid(string):
    try:
        re.match(r'^([a-zA-Z0-9-_]{1,100})$', string).group(0)
    except AttributeError:
        return False
    return True


def ValidName(string):
    if not name_is_valid(string):
        raise AttributeError("Names must be 1-100 characters long and must "
                             "only contain a-z,A-Z,0-9,-,_")
    return string


def lpname_is_valid(string):
    try:
        re.match(r'^([a-z0-9-_]{1,100})$', string).group(0)
    except (TypeError, AttributeError):
        return False
    return True


def ValidLPName(string):
    if not lpname_is_valid(string):
        raise AttributeError("LP names must be 1-100 characters long and "
                             "must only contain a-z,0-9,-,_")
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


class AssemblyCommands(cli_utils.CommandsBase):
    """Commands for working with assemblies.

Available commands:

    solum assembly list
        Print an index of all available assemblies.

    solum assembly show <NAME>
        Print the details of an assembly.

    solum assembly create <NAME> <PLAN_URI> [--description <DESCRIPTION>]
        Create an assembly from a registered plan.

    solum assembly logs <NAME>
        Print an index of all operation logs for an assembly.

    solum assembly delete <NAME>
        Destroy an assembly.
    """

    def create(self):
        """Create an assembly."""
        self.parser.add_argument('name',
                                 type=ValidName,
                                 help="Assembly name")
        self.parser.add_argument('plan_uri',
                                 help="Tenant/project-wide unique "
                                 "plan (uri/uuid or name)")
        self.parser.add_argument('--description',
                                 help="Assembly description")
        self.parser._names['plan_uri'] = 'plan URI'
        args = self.parser.parse_args()
        name = args.name
        plan_uri = args.plan_uri
        if '/' not in plan_uri:
            # might be a plan uuid/name
            # let's try and be helpful and get the real plan_uri.
            plan = self.client.plans.find(name_or_id=args.plan_uri)
            plan_uri = plan.uri
            print('Note: using plan_uri=%s' % plan_uri)

        assembly = self.client.assemblies.create(name=name,
                                                 description=args.description,
                                                 plan_uri=plan_uri)
        fields = ['uuid', 'name', 'description', 'status', 'application_uri',
                  'trigger_uri']
        self._print_dict(assembly, fields, wrap=72)

    def delete(self):
        """Delete an assembly."""
        self.parser.add_argument('assembly_uuid',
                                 help="Assembly uuid or name")
        self.parser._names['assembly_uuid'] = 'assembly'
        args = self.parser.parse_args()
        assem = self.client.assemblies.find(name_or_id=args.assembly_uuid)
        cli_assem.AssemblyManager(self.client).delete(
            assembly_id=str(assem.uuid))

    def list(self):
        """List all assemblies."""
        fields = ['uuid', 'name', 'description', 'status', 'created_at',
                  'updated_at']
        assemblies = self.client.assemblies.list()
        self._print_list(assemblies, fields, sortby_index=5)

    def logs(self):
        """Get Logs."""
        self.parser.add_argument('assembly',
                                 help="Assembly uuid or name")
        args = self.parser.parse_args()
        assem = self.client.assemblies.find(name_or_id=args.assembly)
        loglist = cli_assem.AssemblyManager(self.client).logs(
            assembly_id=str(assem.uuid))

        fields = ["resource_uuid"]
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

    def show(self):
        """Show an assembly's resource."""
        self.parser.add_argument('assembly_uuid',
                                 help="Assembly uuid or name")
        self.parser._names['assembly_uuid'] = 'assembly'
        args = self.parser.parse_args()
        assemblies = self.client.assemblies.find(name_or_id=args.assembly_uuid)
        fields = ['uuid', 'name', 'description', 'status', 'application_uri',
                  'trigger_uri', 'created_at', 'updated_at', 'workflow']
        self._print_dict(assemblies, fields, wrap=72)


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
    """

    def create(self):
        """Create a language pack."""
        self.parser.add_argument('name',
                                 type=ValidLPName,
                                 help="Language pack name.")
        self.parser.add_argument('git_url',
                                 help=("Github url of custom "
                                       "language pack repository."))
        self.parser.add_argument('--lp_metadata',
                                 help="Language pack metadata file.")
        self.parser._names['git_url'] = 'repo URL'
        args = self.parser.parse_args()
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
                lp_metadata=lp_metadata)
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
        """Get Logs."""
        self.parser.add_argument('lp_id',
                                 help="languagepack uuid or name")
        args = self.parser.parse_args()
        loglist = cli_lp.LanguagePackManager(self.client).logs(
            lp_id=str(args.lp_id))

        fields = ["resource_uuid"]
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

        error_message = ("Application name must be 1-100 characters and must "
                         "only contain a-z,A-Z,0-9,-,_")

        if plan_definition.get('name') is not None:
            if not name_is_valid(plan_definition.get('name')):
                raise exc.CommandError(message=error_message)

    def _filter_ready_lps(self, lp_list):
        filtered_list = []
        for lp in lp_list:
            if lp.status == 'READY':
                filtered_list.append(lp)

        return filtered_list

    def list(self):
        """Print a list of all deployed applications."""
        # This is just "plan list".
        # TODO(datsun180b): List each plan and its associated
        # assemblies.
        fields = ['uuid', 'name', 'description']
        plans = self.client.plans.list()
        self._print_list(plans, fields)

    def logs(self):
        """Print a list of all logs belonging to a single app."""
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args = self.parser.parse_args()
        assemblies = self.client.assemblies.list()

        all_logs_list = []
        fields = ["resource_uuid", "created_at"]
        for a in assemblies:
            plan_uuid = a.plan_uri.split('/')[-1]
            if args.app not in [plan_uuid, a.name]:
                continue
            loglist = cli_assem.AssemblyManager(self.client).logs(
                assembly_id=str(a.uuid))

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
                            filtered_list = self._filter_ready_lps([lp1])
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
        error_message = ("Application name must be 1-100 characters and must "
                         "only contain a-z,A-Z,0-9,-,_")
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
                app_name = raw_input("Please name the application.\n> ")
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
            filtered_list = self._filter_ready_lps(languagepacks)

            if len(filtered_list) > 0:
                lpnames = [lang_pack.name for lang_pack in filtered_list]
                lp_uuids = [lang_pack.uuid for lang_pack in filtered_list]
                fields = ['uuid', 'name', 'description',
                          'status', 'source_uri']
                self._print_list(filtered_list, fields)
                languagepack = raw_input("Please choose a languagepack from "
                                         "the above list.\n> ")
                while languagepack not in lpnames + lp_uuids:
                    languagepack = raw_input("You must choose one of the named"
                                             " language packs.\n> ")
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
            git_url = raw_input("Please specify a git repository URL for "
                                "your application.\n> ")
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
            run_cmd = raw_input("Please specify start/run command for your "
                                "application.\n> ")
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
            msg = ("Artifact names must be 1-100 characters long and "
                   "must only contain a-z,0-9,-,_")
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
        fields = ['uuid', 'name', 'description', 'status', 'application_uri',
                  'trigger_uri']
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

    solum lp logs <UUID>
        Show logs for a language pack.


    solum app help
        Show a help message specific to app commands.

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

    solum app delete <NAME|UUID>
        Delete an application and all related artifacts.

    solum app logs <NAME|UUID>
        Show the logs of an application for all the deployments.


    SOON TO BE DEPRECATED:

    solum assembly list
        Print an index of all available assemblies.

    solum assembly create <NAME> <PLAN_URI> [--description <DESCRIPTION>]
        Create an assembly from a registered plan.

    solum assembly delete <NAME|UUID>
        Destroy an assembly.
    """

    parser = PermissiveParser()

    resources = {
        'app': AppCommands,
        'plan': PlanCommands,
        'assembly': AssemblyCommands,
        'pipeline': PipelineCommands,
        'lp': LanguagePackCommands,
        'languagepack': LanguagePackCommands,
        'component': ComponentCommands,

        'info': InfoCommands,
    }

    choices = resources.keys()

    parser.add_argument('resource', choices=choices,
                        default='help',
                        help="Target noun to act upon")

    parser.add_argument('-V', '--version', action='store_true',
                        dest='show_version',
                        help="Report solum version.")

    parsed, _ = parser.parse_known_args()

    if parsed.show_version:
        print("python-solumclient version %s" % solumclient.__version__)
        return

    resource = vars(parsed).get('resource')

    if resource in resources:
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
