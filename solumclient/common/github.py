# Copyright (c) 2015 Rackspace
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

# Tools for interacting with Github.

import base64
import getpass
import json
import random
import re
import string

import httplib2


class GitHubAuth(object):
    username = None
    password = None
    full_repo_name = None
    git_url = None
    _token = None

    _auth_url = 'https://api.github.com/authorizations'

    def __init__(self, git_url):
        self.git_url = git_url

        user_org_name, repo = '', ''

        github_regex = r'github\.com[:/](.+?)/(.+?)($|/$|\.git$|\.git/$)'
        repo_pat = re.compile(github_regex)
        match = repo_pat.search(self.git_url)
        if match:
            user_org_name, repo = match.group(1), match.group(2)
        else:
            raise ValueError("Failed to parse %s." % git_url)
        self.full_repo_name = '/'.join([user_org_name, repo])
        prompt = ("Username for repo '%s' [%s]:" %
                  (self.full_repo_name, user_org_name))
        username = raw_input(prompt) or user_org_name
        password = getpass.getpass("Password: ")
        self.username = username
        self.password = password

    @property
    def _auth_header(self):
        authstring = '%s:%s' % (self.username, self.password)
        auth = base64.encodestring(authstring)
        return {
            'Authorization': 'Basic %s' % auth,
            'Content-Type': 'application/json',
            }

    @property
    def token(self):
        if self._token is None:
            self._get_repo_token()
        return self._token

    def _get_repo_token(self):
        note = ''.join(random.sample(string.lowercase, 5))
        auth_info = {
            'scopes': 'repo',
            'note': 'Solum-status-%s' % note,
            }
        resp, content = httplib2.Http().request(
            self._auth_url,
            'POST',
            headers=self._auth_header,
            body=json.dumps(auth_info))
        if resp.get('status') in ['200', '201']:
            response_body = json.loads(content)
            self._token = response_body.get('token')

    def create_webhook(self, trigger_uri):
        hook_url = ('https://api.github.com/repos/%s/hooks' %
                    self.full_repo_name)
        hook_info = {
            'name': 'web',
            'events': ['pull_request', 'commit_comment'],
            'config': {
                'content_type': 'json',
                'url': trigger_uri,
            }
        }
        resp, content = httplib2.Http().request(
            hook_url,
            'POST',
            headers=self._auth_header,
            body=json.dumps(hook_info))
        if resp.get('status') not in ['200', '201']:
            pass

    def add_ssh_key(self, public_key=None, is_private=False):
        if not public_key:
            return
        api_url = ('https://api.github.com/repos/%s/keys' %
                   self.full_repo_name)
        if is_private:
            api_url = 'https://api.github.com/user/keys'
        key_info = {
            'title': 'devops@Solum',
            'key': public_key,
            }
        resp, content = httplib2.Http().request(
            api_url,
            'POST',
            headers=self._auth_header,
            body=json.dumps(key_info))
        if resp.get('status') not in ['200', '201']:
            pass
