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


class CommandsBase(object):
    """Base command parsing class."""
    parser = None
    solum = None

    def __init__(self, parser):
        self.parser = parser
        self._get_global_flags()
        self.parser.add_argument('action',
                                 default='help',
                                 help='Action to perform on resource')
        action = None

        try:
            parsed, _ = parser.parse_known_args()
            action = parsed.action
        except Exception:
            # Parser has a habit of doing this when an arg is missing.
            self.parser.print_help()

        if action in self._actions:
            try:
                self.parser.error = self.parser.the_error
                self._actions[action]()
            except Exception:
                print(self._actions[action].__doc__)
                self.parser.print_help()

    @property
    def _actions(self):
        """Action handler"""
        return dict((attr, getattr(self, attr))
                    for attr in dir(self)
                    if not attr.startswith('_')
                    and callable(getattr(self, attr)))

    def _get_global_flags(self):
        """Get global flags."""
        # Good location to add_argument() global options like --verbose
        pass

    def help(self):
        """Print this help message."""
        print(self.__doc__)
        show_help(self._actions, 'actions')


def show_help(resources, name='targets or nouns'):
    """Help screen."""
    print("Full list of commands:")
    print("  app create [--repo=repo_url] [--build=no] plan_name")
    print("  app delete plan_name")
    print("  app list")
    print("  assembly create [--assembly=assembly_name] plan_name")
    print("  assembly delete assembly_name")
    print("  assembly list")
    print("\n")

    print("Available %s:" % name)
    for resource in sorted(resources):
        commands = resources.get(resource)
        docstring = "<%s %s>" % (name.capitalize(), resource)
        if commands.__doc__:
            docstring = commands.__doc__
        print("\t%-20s%s" % (resource, docstring))
