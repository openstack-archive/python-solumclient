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
* languagepack create lp_file
* languagepack list
* languagepack show lp_id
* languagepack delete lp_id
* languagepack build lp_name git_url lp_metadata_file
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
import sys

from solumclient.common import cli_utils
from solumclient.common import exc
from solumclient.common import yamlutils
from solumclient.openstack.common import cliutils
from solumclient.v1 import assembly as cli_assem
from solumclient.v1 import pipeline as cli_pipe
from solumclient.v1 import plan as cli_plan


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
        args, _ = self.parser.parse_known_args()
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
        data = dict([(f, getattr(plan, f, ''))
                     for f in fields])
        artifacts = copy.deepcopy(data['artifacts'])
        del data['artifacts']
        cliutils.print_dict(data, wrap=72)
        self._show_public_keys(artifacts)

    def delete(self):
        """Delete a plan."""
        self.parser.add_argument('plan_uuid',
                                 help="Tenant/project-wide unique "
                                 "plan uuid or name")
        self.parser._names['plan_uuid'] = 'plan'
        args, _ = self.parser.parse_known_args()
        plan = self.client.plans.find(name_or_id=args.plan_uuid)
        cli_plan.PlanManager(self.client).delete(plan_id=str(plan.uuid))

    def show(self):
        """Show a plan's resource."""
        self.parser.add_argument('plan_uuid',
                                 help="Plan uuid or name")
        self.parser._names['plan_uuid'] = 'plan'
        args, _ = self.parser.parse_known_args()
        response = self.client.plans.find(name_or_id=args.plan_uuid)
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts']
        data = dict([(f, getattr(response, f, ''))
                     for f in fields])
        artifacts = copy.deepcopy(data['artifacts'])
        del data['artifacts']
        cliutils.print_dict(data, wrap=72)
        self._show_public_keys(artifacts)

    def list(self):
        """List all plans."""
        fields = ['uuid', 'name', 'description']
        response = self.client.plans.list()
        cliutils.print_list(response, fields)

    def _show_public_keys(self, artifacts):
        public_keys = {}
        if artifacts:
            for arti in artifacts:
                if arti.content and ('public_key' in arti.content):
                    public_keys.update(
                        {arti.content['href']: arti.content['public_key']})
        if public_keys:
            print('Important:')
            print('  Solum has generated SSH keypair for your ' +
                  'private github repository/ies.')
            print('  Please add these public SSH keys as github deploy keys.')
            print('  This enables solum assembly create to securely ' +
                  'clone/pull your private repository/ies.')
            print('  More details on github deploy keys: ' +
                  'https://developer.github.com/guides/' +
                  'managing-deploy-keys/#deploy-keys\n')
            for href, pub_key in public_keys.items():
                print('%s :\n  %s' % (href, pub_key))


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
                                 help="Assembly name")
        self.parser.add_argument('plan_uri',
                                 help="Tenant/project-wide unique "
                                 "plan (uri/uuid or name)")
        self.parser.add_argument('--description',
                                 help="Assembly description")
        self.parser._names['plan_uri'] = 'plan URI'
        args, _ = self.parser.parse_known_args()
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
        data = dict([(f, getattr(assembly, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)

    def delete(self):
        """Delete an assembly."""
        self.parser.add_argument('assembly_uuid',
                                 help="Assembly uuid or name")
        self.parser._names['assembly_uuid'] = 'assembly'
        args, _ = self.parser.parse_known_args()
        assem = self.client.assemblies.find(name_or_id=args.assembly_uuid)
        cli_assem.AssemblyManager(self.client).delete(
            assembly_id=str(assem.uuid))

    def list(self):
        """List all assemblies."""
        fields = ['uuid', 'name', 'description', 'status', 'created_at',
                  'updated_at']
        response = self.client.assemblies.list()
        cliutils.print_list(response, fields, sortby_index=5)

    def logs(self):
        """Get Logs."""
        self.parser.add_argument('assembly',
                                 help="Assembly uuid or name")
        args, _ = self.parser.parse_known_args()
        assem = self.client.assemblies.find(name_or_id=args.assembly)
        response = cli_assem.AssemblyManager(self.client).logs(
            assembly_id=str(assem.uuid))

        fields = ["assembly_uuid"]
        for log in response:
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

        cliutils.print_list(response, fields)

    def show(self):
        """Show an assembly's resource."""
        self.parser.add_argument('assembly_uuid',
                                 help="Assembly uuid or name")
        self.parser._names['assembly_uuid'] = 'assembly'
        args, _ = self.parser.parse_known_args()
        response = self.client.assemblies.find(name_or_id=args.assembly_uuid)
        fields = ['uuid', 'name', 'description', 'status', 'application_uri',
                  'trigger_uri', 'created_at', 'updated_at']
        data = dict([(f, getattr(response, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)


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
        args, _ = self.parser.parse_known_args()
        response = self.client.components.find(name_or_id=args.component_uuid)
        fields = ['uuid', 'name', 'description', 'uri', 'assembly_uuid']
        data = dict([(f, getattr(response, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)

    def list(self):
        """List all components."""
        fields = ['uuid', 'name', 'description', 'assembly_uuid']
        response = self.client.components.list()
        cliutils.print_list(response, fields)


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
                                 help="Pipeline name")
        self.parser._names['plan_uri'] = 'plan URI'
        self.parser._names['workbook_name'] = 'workbook'
        args, _ = self.parser.parse_known_args()
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
        data = dict([(f, getattr(pipeline, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)

    def delete(self):
        """Delete an pipeline."""
        self.parser.add_argument('pipeline_uuid',
                                 help="Pipeline uuid or name")
        self.parser._names['pipeline_uuid'] = 'pipeline'
        args, _ = self.parser.parse_known_args()
        pipeline = self.client.pipelines.find(name_or_id=args.pipeline_uuid)
        cli_pipe.PipelineManager(self.client).delete(
            pipeline_id=str(pipeline.uuid))

    def list(self):
        """List all pipelines."""
        fields = ['uuid', 'name', 'description']
        response = self.client.pipelines.list()
        cliutils.print_list(response, fields)

    def show(self):
        """Show a pipeline's resource."""
        self.parser.add_argument('pipeline_uuid',
                                 help="Pipeline uuid or name")
        self.parser._names['pipeline_uuid'] = 'pipeline'
        args, _ = self.parser.parse_known_args()
        response = self.client.pipelines.find(name_or_id=args.pipeline_uuid)
        fields = ['uuid', 'name', 'description',
                  'trigger_uri', 'workbook_name', 'last_execution']
        data = dict([(f, getattr(response, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)


class LanguagePackCommands(cli_utils.CommandsBase):
    """Commands for working with language packs.

Available commands:

    solum languagepack list
        Print and index of all available language packs.

    solum languagepack show <LP>
        Print the details of a language pack.

    solum languagepack create <LPFILE>
        Create a new language pack from a file.

    solum languagepack build <NAME> <GIT_REPO> <METADATA>
        Create a new language pack from a git repo.

    solum languagepack delete <LP>
        Destroy a language pack.

    """

    def create(self):
        """Create a language pack."""
        self.parser.add_argument('lp_file',
                                 help="Language pack file.")
        self.parser._names['lp_file'] = 'languagepack file'
        args, _ = self.parser.parse_known_args()
        with open(args.lp_file) as lang_pack_file:
            try:
                data = json.load(lang_pack_file)
            except ValueError as exc:
                print("Error in language pack file: %s", str(exc))
                sys.exit(1)

        languagepack = self.client.languagepacks.create(**data)
        fields = ['uuid', 'name', 'description', 'compiler_versions',
                  'os_platform']
        data = dict([(f, getattr(languagepack, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)

    def delete(self):
        """Delete a language pack."""
        self.parser.add_argument('lp_id',
                                 help="Language pack id")
        self.parser._names['lp_id'] = 'languagepack'
        args, _ = self.parser.parse_known_args()
        self.bldclient.images.delete(lp_id=args.lp_id)

    def list(self):
        """List all language packs."""
        fields = ['uuid', 'name', 'description', 'state', 'source_uri']
        response = self.bldclient.images.list()
        cliutils.print_list(response, fields)

    def show(self):
        """Get a language pack."""
        self.parser.add_argument('lp_uuid',
                                 help="Language pack id")
        self.parser._names['lp_uuid'] = 'languagepack'
        args, _ = self.parser.parse_known_args()
        response = self.bldclient.images.find(lp_uuid=args.lp_uuid)
        fields = ['uuid', 'name', 'description', 'state', 'source_uri']
        data = dict([(f, getattr(response, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)

    def build(self):
        """Build a custom language pack."""
        self.parser.add_argument('name',
                                 help="Language pack name.")
        self.parser.add_argument('git_url',
                                 help=("Github url of custom "
                                       "language pack repository."))
        self.parser.add_argument('--lp_metadata',
                                 help="Language pack file.")
        self.parser._names['git_url'] = 'repo URL'
        args, _ = self.parser.parse_known_args()
        lp_metadata = None

        if args.lp_metadata:
            with open(args.lp_metadata) as lang_pack_metadata:
                try:
                    lp_metadata = json.dumps(json.load(lang_pack_metadata))
                except ValueError as exc:
                    print("Error in language pack file: %s", str(exc))
                    sys.exit(1)
        response = self.bldclient.images.create(name=args.name,
                                                source_uri=args.git_url,
                                                lp_metadata=lp_metadata)
        fields = ['uuid', 'name', 'decription', 'state']
        data = dict([(f, getattr(response, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)


class AppCommands(cli_utils.CommandsBase):
    """Commands for working with applications.

Available commands:
    solum app list
        Print an index of all deployed applications.

    solum app show <APP>
        Print detailed information about one application.

    solum app create [--planfile <PLANFILE>] [--git-url <GIT_URL>]
                     [--langpack <LANGPACK>] [--run-cmd <RUN_CMD>]
                     [--name <NAME>] [--desc <DESCRIPTION>]
        Register a new application with Solum.

    solum app deploy <APP>
        Deploy an application, building any applicable artifacts first.

    solum app delete <APP>
        Delete an application and all related artifacts.
"""

    def _get_assemblies_by_plan(self, plan):
        # TODO(datsun180b): Write this.
        return []

    def _show_public_keys(self, artifacts):
        # Shamelessly plucked from PlanCommands.
        public_keys = {}
        if artifacts:
            for arti in artifacts:
                if arti.content and ('public_key' in arti.content):
                    public_keys.update(
                        {arti.content['href']: arti.content['public_key']})
        if public_keys:
            print('Important:')
            print('  Solum has generated SSH keypair for your ' +
                  'private github repository/ies.')
            print('  Please add these public SSH keys as github deploy keys.')
            print('  This enables solum assembly create to securely ' +
                  'clone/pull your private repository/ies.')
            print('  More details on github deploy keys: ' +
                  'https://developer.github.com/guides/' +
                  'managing-deploy-keys/#deploy-keys\n')
            for href, pub_key in public_keys.items():
                print('%s :\n  %s' % (href, pub_key))

    def list(self):
        """Print a list of all deployed applications."""
        # This is just "assembly list".
        # TODO(datsun180b): List each plan and its associated
        # assemblies.
        fields = ['uuid', 'name', 'description', 'status', 'created_at',
                  'updated_at']
        assemblies = self.client.assemblies.list()
        cliutils.print_list(assemblies, fields, sortby_index=5)

    def show(self):
        """Print detailed information about one application."""
        # This is just "plan show <PLAN>".
        # TODO(datsun180b): List the details of the plan, and
        # also the current build state, build number, and running
        # assembly status. We don't have all the pieces for that yet.
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args, _ = self.parser.parse_known_args()
        plan = self.client.plans.find(name_or_id=args.app)
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts']
        data = dict([(f, getattr(plan, f, ''))
                     for f in fields])
        artifacts = copy.deepcopy(data['artifacts'])
        del data['artifacts']
        cliutils.print_dict(data, wrap=72)
        self._show_public_keys(artifacts)

    def create(self):
        """Register a new application with Solum."""
        # This is just "plan create" with a little proactive
        # parsing of the planfile.

        self.parser.add_argument('--planfile',
                                 help="Local planfile location")
        self.parser.add_argument('--git-url',
                                 help='Source repo')
        self.parser.add_argument('--langpack',
                                 help='Language pack')

        self.parser.add_argument('--run-cmd',
                                 help="Application entry point")
        self.parser.add_argument('--name',
                                 help="Application name")
        self.parser.add_argument('--desc',
                                 help="Application description")
        self.parser.add_argument('--param-file',
                                 dest='param_file',
                                 help="A yaml file containing custom"
                                      " parameters to be used in the"
                                      " application")

        args, _ = self.parser.parse_known_args()

        # Get the plan file. Either get it from args, or supply
        # a skeleton.
        plan_definition = None
        if args.planfile is not None:
            planfile = args.planfile
            try:
                with open(planfile) as definition_file:
                    definition = definition_file.read()
                    plan_definition = yamlutils.load(definition)
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
                    'content': {},
                    }]}

        # NOTE: This assumes the plan contains exactly one artifact.

        # Check for the language pack. Check args first, then planfile.
        # If it's neither of those places, prompt for it and update the
        # plan definition.
        langpack = None
        if args.langpack is not None:
            plan_definition['artifacts'][0]['language_pack'] = args.langpack
        elif plan_definition['artifacts'][0].get('language_pack') is None:
            langpacks = self.client.languagepacks.list()
            lpnames = [lp.name for lp in langpacks]
            fields = ['uuid', 'name', 'description', 'compiler_versions',
                      'os_platform']
            cliutils.print_list(langpacks, fields)
            langpack = raw_input("Please choose a languagepack from the "
                                 "above list.\n> ")
            while langpack not in lpnames:
                langpack = raw_input("You must choose one of the named "
                                     "language packs.\n> ")
            plan_definition['artifacts'][0]['language_pack'] = langpack

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

        # Check for the entry point. Check args first, then the planfile.
        # If it's neither of those places, prompt for it and update the
        # plan definition.
        '''
        run_cmd = None
        if args.run_cmd is not None:
            plan_definition['artifacts'][0]['run_cmd'] = args.run_cmd
        if plan_definition['artifacts'][0].get('run_cmd') is None:
            run_cmd = raw_input("Please specify an entry point for your "
                                "application.\n> ")
            plan_definition['artifacts'][0]['run_cmd'] = run_cmd
        '''

        # Update name and description if specified.
        if args.name is not None:
            plan_definition['name'] = args.name
        if not plan_definition.get('name'):
            name = ''
            while not name:
                name = raw_input("Please name the application.\n> ")
            plan_definition['name'] = name

        if args.desc is not None:
            plan_definition['description'] = args.desc

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
        fields = ['uuid', 'name', 'description', 'uri', 'artifacts']
        data = dict([(f, getattr(plan, f, ''))
                     for f in fields])
        artifacts = copy.deepcopy(data['artifacts'])
        del data['artifacts']
        cliutils.print_dict(data, wrap=72)
        self._show_public_keys(artifacts)

    def deploy(self):
        """Deploy an application, building any applicable artifacts first."""
        # This is just "assembly create" with a little bit of introspection.
        # TODO(datsun180b): Add build() method, and add --build-id argument
        # to this method to allow for build-only and deploy-only workflows.
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args, _ = self.parser.parse_known_args()
        plan = self.client.plans.find(name_or_id=args.app)

        assembly = self.client.assemblies.create(name=plan.name,
                                                 description=plan.description,
                                                 plan_uri=plan.uri)
        fields = ['uuid', 'name', 'description', 'status', 'application_uri',
                  'trigger_uri']
        data = dict([(f, getattr(assembly, f, ''))
                     for f in fields])
        cliutils.print_dict(data, wrap=72)

    def delete(self):
        """Delete an application and all related artifacts."""
        # This is "assembly delete" followed by "plan delete".
        self.parser.add_argument('app',
                                 help="Application name")
        self.parser._names['app'] = 'application'
        args, _ = self.parser.parse_known_args()
        plan = self.client.plans.find(name_or_id=args.app)
        assemblies = [a for a in self.client.assemblies.list()
                      if a.plan_uri.split('/')[-1] == plan.uuid]
        for assembly in assemblies:
            assem = self.client.assemblies.find(name_or_id=assembly.uuid)
            cli_assem.AssemblyManager(self.client).delete(
                assembly_id=str(assem.uuid))

        cli_plan.PlanManager(self.client).delete(plan_id=str(plan.uuid))


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

    def parse_known_args(self, *args, **kwargs):
        # Instead of sys.exit(), how about we just hand back an
        # empty Namespace and let someone else decide when to exit.
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

For a complete description, please see README-CLI.rst.
Available commands:

    solum help
        Show this help message.


    solum app list
        Print an index of all deployed applications.

    solum app show <APP>
        Print detailed information about one application.

    solum app create [--planfile <PLANFILE>] [--git-url <GIT_URL>]
                     [--langpack <LANGPACK>] [--run-cmd <RUN_CMD>]
                     [--name <NAME>] [--desc <DESCRIPTION>]
        Register a new application with Solum.

    solum app deploy <APP>
        Deploy an application, building any applicable artifacts first.

    solum app delete <APP>
        Delete an application and all related artifacts.


    solum plan list
        Print an index of all available plans.

    solum plan show <PLAN>
        Print details about a plan.

    solum plan create <PLANFILE> [--param-file <PARAMFILE>]
        Register a plan with Solum.

    solum plan delete <PLAN>
        Destroy a plan. Plans with dependent assemblies cannot be deleted.


    solum assembly list
        Print an index of all available assemblies.

    solum assembly create <NAME> <PLAN_URI> [--description <DESCRIPTION>]
        Create an assembly from a registered plan.

    solum assembly delete <PLAN>
        Destroy an assembly.


    solum component list
        Print an index of all available components.

    solum component show <UUID>
        Print details about a component.


    solum pipeline list
        Print an index of all available pipelines.

    solum pipeline show <PIPELINE>
        Print details about a pipeline.

    solum pipeline create <PLAN_URI> <WORKBOOK_NAME> <NAME>
        Create a pipeline from a given workbook and registered plan.

    solum pipeline delete <PIPELINE>
        Destroy a pipeline.
    """

    parser = PermissiveParser()

    resources = {
        'app': AppCommands,
        'plan': PlanCommands,
        'assembly': AssemblyCommands,
        'pipeline': PipelineCommands,
        'languagepack': LanguagePackCommands,
        'component': ComponentCommands,
    }

    choices = resources.keys()

    parser.add_argument('resource', choices=choices,
                        default='help',
                        help="Target noun to act upon")

    parsed, _ = parser.parse_known_args()
    resource = vars(parsed).get('resource')

    if resource in resources:
        try:
            resources[resource](parser)
        except Exception as e:
            print("ERROR: %s" % e.message)

    else:
        print(main.__doc__)

if __name__ == '__main__':
    sys.exit(main())
