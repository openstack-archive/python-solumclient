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
* app create --repo="repo_url" [--build=no] plan_name
* app delete plan_name
* app list
* assembly create [--assembly="assembly_name"] plan_name
* assembly delete assembly_name
* assembly list

Notes:
* This code is expected to be replaced by the OpenStack Client (OSC) when
    it has progressed a little bit farther as described at:
    https://wiki.openstack.org/wiki/Solum/CLI
* Internationalization will not be added in M1 since this is a prototype
"""

import argparse
import sys

from solumclient.common import cli_utils


SOLUM_CLI_VER = "2014-01-30"


class AppCommands(cli_utils.CommandsBase):
    """Application targets."""

    def create(self):
        """Create an application."""
        self.parser.add_argument('plan_name',
                                 help="Tenant/project-wide unique plan name")
        self.parser.add_argument('--repo',
                                 help="Code repository URL")
        self.parser.add_argument('--build',
                                 default='yes',
                                 help="Build flag")
        args = self.parser.parse_args()
        #TODO(noorul): Add REST communications
        print("app create plan_name=%s repo=%s build=%s" % (
            args.plan_name,
            args.repo,
            args.build))

    def delete(self):
        """Delete an application."""
        self.parser.add_argument('plan_name',
                                 help="Tenant/project-wide unique plan name")
        args = self.parser.parse_args()
        #TODO(noorul): Add REST communications
        print("app delete plan_name=%s" % (
            args.plan_name))

    def list(self):
        """List all applications."""
        #TODO(noorul): Add REST communications
        print("app list")


class AssemblyCommands(cli_utils.CommandsBase):
    """Assembly targets."""

    def create(self):
        """Create an assembly."""
        self.parser.add_argument('plan_name',
                                 help="Tenant/project-wide unique plan name")
        self.parser.add_argument('--assembly',
                                 help="Assembly name")
        args = self.parser.parse_args()
        #TODO(noorul): Add REST communications
        print("assembly create plan_name=%s assembly=%s" % (
            args.plan_name,
            args.assembly))

    def delete(self):
        """Delete an assembly."""
        self.parser.add_argument('assembly_name',
                                 help="Assembly name")
        args = self.parser.parse_args()
        #TODO(noorul): Add REST communications
        print("assembly delete assembly_name=%s" % (
            args.assembly_name))

    def list(self):
        """List all assemblies."""
        #TODO(noorul): Add REST communications
        print("assembly list")


def main():
    """Basically the entry point."""
    print("Solum Python Command Line Client %s\n" % SOLUM_CLI_VER)
    parser = argparse.ArgumentParser(conflict_handler='resolve')
    parser.the_error = parser.error
    parser.error = lambda m: None

    resources = {
        'app': AppCommands,
        'assembly': AssemblyCommands,
    }

    choices = resources.keys()

    parser.add_argument('resource', choices=choices,
                        help="Target noun to act upon")

    resource = None
    try:
        parsed, _ = parser.parse_known_args()
        resource = parsed.resource
    except Exception as se_except:
        parser.print_help()
        return se_except

    if resource in resources:
        resources[resource](parser)
    else:
        cli_utils.show_help(resources)
        print("\n")
        parser.print_help()

if __name__ == '__main__':
    sys.exit(main())
