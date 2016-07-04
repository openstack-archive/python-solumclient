#!/usr/bin/env python
# Copyright 2014 - Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
Setup everything for a Github-hosted repo to use solum as its CI tool.
"""

import argparse
import base64
import getpass
import json
import os
import random
import re
import string
import tempfile

import httplib2
import six
import yaml

from solumclient import client as solum_client
from solumclient.openstack.common import cliutils


SOLUM_API_VERSION = '1'
CREDENTIALS = {}
PLAN_TEMPLATE = {"version": 1,
                 "name": "chef",
                 "description": "chef testy",
                 "artifacts": []}


def _get_solum_client():
    args = {}
    args['os_username'] = os.getenv('OS_USERNAME', '')
    args['os_password'] = os.getenv('OS_PASSWORD', '')
    args['os_tenant_name'] = os.getenv('OS_TENANT_NAME', '')
    args['os_auth_url'] = os.getenv('OS_AUTH_URL', '')
    args['solum_url'] = os.getenv('SOLUM_URL', '')

    try:
        client = solum_client.get_client(SOLUM_API_VERSION, **args)
        return client
    except Exception as ex:
        print("Error in getting Solum client: %s" % ex)
        exit(1)


def _get_token(git_url):
    # Get an OAuth token with the scope of 'repo' for the user
    if git_url in CREDENTIALS and 'token' in CREDENTIALS[git_url]:
        return CREDENTIALS[git_url]['token']

    repo_pat = re.compile(r'github\.com[:/](.+?)/(.+?)($|/$|\.git$|\.git/$)')
    match = repo_pat.search(git_url)
    if match:
        user_org_name = match.group(1)
        repo = match.group(2)
    else:
        print('Failed parsing %s' % git_url)
        exit(1)

    full_repo_name = '/'.join([user_org_name, repo])
    username = six.moves.input("Username for repo '%s' [%s]: " %
                               (full_repo_name, user_org_name))
    if not username:
        username = user_org_name
    password = getpass.getpass("Password: ")
    # TODO(james_li): add support for two-factor auth
    CREDENTIALS[git_url] = {}
    CREDENTIALS[git_url]['user'] = username
    CREDENTIALS[git_url]['password'] = password
    CREDENTIALS[git_url]['full_repo'] = full_repo_name

    http = httplib2.Http()
    auth = base64.encodestring(username + ':' + password)
    headers = {'Authorization': 'Basic ' + auth,
               'Content-Type': 'application/json'}
    # 'note' field has to be unique
    note = 'Solum-status-' + ''.join(random.sample(string.lowercase, 5))
    data = {'scopes': 'repo', 'note': note}

    # TODO(james_li): make the url configurable
    resp, content = http.request('https://api.github.com/authorizations',
                                 'POST', headers=headers,
                                 body=json.dumps(data))

    if resp['status'] == '201' or resp['status'] == '200':
        content_dict = json.loads(content)
        CREDENTIALS[git_url]['token'] = str(content_dict['token'])
        return CREDENTIALS[git_url]['token']
    else:
        print('Failed to get token from Github')
        exit(1)


def _filter_trigger_url(url):
    filtered_url = url
    url_pattern = re.compile(r'^(http://)(.+)')
    match = url_pattern.search(url)
    if match:
        filtered_url = ''.join(['https://', match.group(2)])
    else:
        print('Cannot filter trigger url, to use the original one')
    return filtered_url


def get_planfile(git_uri, app_name, cmd, public):
    plan_dict = dict.copy(PLAN_TEMPLATE)
    plan_dict['name'] = app_name
    plan_dict['description'] = git_uri  # Put repo uri as plan desc.
    arti = {"name": "chef", "artifact_type": "chef",
            "content": {}, "language_pack": "auto"}
    arti['content']['href'] = git_uri
    if not public:
        arti['content']['private'] = True
    arti['unittest_cmd'] = cmd
    plan_dict['artifacts'].append(arti)

    # Create a Github token and insert it into plan file
    for arti in plan_dict['artifacts']:
        arti['status_token'] = _get_token(arti['content']['href'])
    plan_file = tempfile.NamedTemporaryFile(suffix='.yaml',
                                            prefix='solum_',
                                            delete=False)
    plan_file.write(yaml.dump(plan_dict, default_flow_style=False))
    plan_file_name = plan_file.name
    plan_file.close()
    return plan_file_name


def create_plan(client, plan_file):
    cmd = ['solum', 'app', 'create', plan_file]
    print(' '.join(cmd))
    with open(plan_file) as definition_file:
        definition = definition_file.read()

    plan = client.plans.create(definition)
    fields = ['uuid', 'name', 'description', 'uri']
    data = dict([(f, getattr(plan, f, ''))
                 for f in fields])
    cliutils.print_dict(data, wrap=72)

    if data['uri'] is None:
        print('Error: no uri found in plan creation')
        exit(1)

    # get public keys in the case of private repos
    artifacts = getattr(plan, 'artifacts', [])
    for arti in artifacts:
        content = getattr(arti, 'content', {})
        if 'public_key' in content and 'href' in content:
            CREDENTIALS[content['href']]['pub_key'] = content['public_key']

    return data['uri']


def create_assembly(client, app_name, plan_uri):
    cmd = ['solum', 'assembly', 'create', app_name, plan_uri]
    print(' '.join(cmd))
    assembly = client.assemblies.create(name=app_name, plan_uri=plan_uri)

    fields = ['uuid', 'name', 'description', 'status', 'application_uri',
              'trigger_uri']
    data = dict([(f, getattr(assembly, f, ''))
                 for f in fields])
    cliutils.print_dict(data, wrap=72)

    trigger_uri = data['trigger_uri']
    if trigger_uri is None:
        print('Error in trigger uri')
        exit(1)

    return trigger_uri


def create_webhook(trigger_uri):
    # Create github web hooks for pull requests
    for key in CREDENTIALS.keys():
        user = CREDENTIALS[key]['user']
        password = CREDENTIALS[key]['password']
        auth = base64.encodestring(user + ':' + password)
        http = httplib2.Http()
        # TODO(james_li): make this url configurable
        github_url = ('https://api.github.com/repos/%s/hooks' %
                      CREDENTIALS[key]['full_repo'])
        headers = {'Authorization': 'Basic ' + auth,
                   'Content-Type': 'application/json'}
        data = {'name': 'web',
                'events': ['pull_request', 'commit_comment'],
                'config': {'content_type': 'json',
                           'url': trigger_uri}}

        resp, _ = http.request(github_url, 'POST',
                               headers=headers,
                               body=json.dumps(data))

        if resp['status'] != '201' and resp['status'] != '200':
            print("Failed to create web hooks")
            print("Make sure you have access to repo '%s'" % key)
            exit(1)


def add_ssh_keys(args):
    if args.public:
        return

    # add public keys
    for key in CREDENTIALS.keys():
        if ('pub_key' in CREDENTIALS[key] and
                CREDENTIALS[key]['pub_key'] is not None):
            user = CREDENTIALS[key]['user']
            password = CREDENTIALS[key]['password']
            auth = base64.encodestring(user + ':' + password)
            http = httplib2.Http()
            if args.user_key:
                # TODO(james_li): make the url configurable
                github_url = 'https://api.github.com/user/keys'
            else:
                github_url = ('https://api.github.com/repos/%s/keys' %
                              CREDENTIALS[key]['full_repo'])
            headers = {'Authorization': 'Basic ' + auth,
                       'Content-Type': 'application/json'}
            data = {'title': 'devops@Solum',
                    'key': CREDENTIALS[key]['pub_key']}

            resp, _ = http.request(github_url, 'POST',
                                   headers=headers,
                                   body=json.dumps(data))

            if resp['status'] != '201' and resp['status'] != '200':
                if args.user_key:
                    print("Failed to add a ssh key to the account %s" % user)
                else:
                    print("Failed to add a deploy key to the repo %s" % key)
                exit(1)


def validate_args(args):
    if len(args.command) == 0 or len(args.git_uri) == 0:
        print("Please input for --test-cmd and --git-uri")
        exit(1)

    # try to use a correct git uri
    pat = re.compile(r'github\.com[:/](.+?)/(.+?)($|/.*$|\.git$|\.git/.*$)')
    match = pat.search(args.git_uri)
    if match:
        user_org_name = match.group(1)
        repo = match.group(2)
        if args.public:
            correct_uri = 'https://github.com/%s/%s' % (user_org_name, repo)
        else:
            correct_uri = 'git@github.com:%s/%s.git' % (user_org_name, repo)
        return correct_uri
    else:
        print("The input git uri seems not right")
        if args.public:
            print("The correct format is: https://github.com/<USER>/<REPO>")
        else:
            print("The correct format is: git@github.com:<USER>/<REPO>.git")
        exit(1)


def main(args):
    git_uri = validate_args(args)
    client = _get_solum_client()
    plan_file = get_planfile(git_uri, args.app_name, args.command, args.public)
    print('\n')
    print("************************* Starting setup *************************")
    print('\n')
    plan_uri = create_plan(client, plan_file)
    add_ssh_keys(args)
    try:
        os.remove(plan_file)
    except OSError:
        print('Cannot remove %s. Skip and move forward...' % plan_file)

    trigger_uri = create_assembly(client, args.app_name, plan_uri)
    create_webhook(_filter_trigger_url(trigger_uri))
    print('Successfully created Solum plan, assembly and webhooks!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app_name', help="app name")
    parser.add_argument('--git-uri', required=True, dest='git_uri',
                        help="git repo uri")
    parser.add_argument('--test-cmd', required=True, dest='command',
                        help="entrypoint to run tests")
    parser.add_argument('--public', action='store_true', default=False,
                        dest='public', help="public repo, defaults to False")
    parser.add_argument('--user-key', action='store_true', default=False,
                        dest='user_key', help="add SSH key to the user account"
                                              " rather than the repo,"
                                              " defaults to False")

    args = parser.parse_args()
    main(args)
