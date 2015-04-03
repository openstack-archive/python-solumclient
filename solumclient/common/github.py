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
    _username = None
    _password = None
    _onetime_password = None
    _token = None
    user_org_name = None
    full_repo_name = None
    git_url = None

    _auth_url = 'https://api.github.com/authorizations'

    def __init__(self, git_url, username=None, password=None):
        self.git_url = git_url

        user_org_name, repo = '', ''

        github_regex = r'github\.com[:/](.+?)/(.+?)($|/$|\.git$|\.git/$)'
        repo_pat = re.compile(github_regex)
        match = repo_pat.search(self.git_url)
        if match:
            user_org_name, repo = match.group(1), match.group(2)
        else:
            raise ValueError("Failed to parse %s." % git_url)

        self.user_org_name = user_org_name

        self.full_repo_name = '/'.join([user_org_name, repo])

        self._username = username
        self._password = password

        # If either is None, ask for them now.
        self.username, self.password

    @property
    def username(self):
        if self._username is None:
            prompt = ("Username for repo '%s' [%s]:" %
                      (self.full_repo_name, self.user_org_name))
            self.username = raw_input(prompt) or self.user_org_name
        return self._username

    @property
    def password(self):
        if self._password is None:
            self._password = getpass.getpass("Password: ")
        return self._password

    @property
    def onetime_password(self):
        if self._onetime_password is None:
            self._onetime_password = getpass.getpass("2FA Token: ")
        return self._onetime_password

    @property
    def token(self):
        if self._token is None:
            self._get_repo_token()
        return self._token

    def _auth_header(self, use_otp=False):
        authstring = '%s:%s' % (self.username, self.password)
        auth = ''
        try:
            auth = base64.encodestring(authstring)
        except TypeError:
            # Python 3
            auth = base64.encodestring(bytes(authstring, 'utf-8'))
        header = {
            'Authorization': 'Basic %s' % auth,
            'Content-Type': 'application/json',
            }
        if use_otp:
            header['x-github-otp'] = self.onetime_password
        return header

    def _get_repo_token(self):
        note = ''.join(random.sample(string.lowercase, 5))
        auth_info = {
            'scopes': 'repo',
            'note': 'Solum-status-%s' % note,
            }
        resp, content = httplib2.Http().request(
            self._auth_url,
            'POST',
            headers=self._auth_header(),
            body=json.dumps(auth_info))
        if resp.get('status') in ['200', '201']:
            response_body = json.loads(content)
            self._token = response_body.get('token')
        else:
            print("Error getting repo token.")

    def _send_authed_request(self, url, body_dict):
        resp, content = httplib2.Http().request(
            url,
            'POST',
            headers=self._auth_header(),
            body=json.dumps(body_dict))
        if resp.get('status') in ['401']:
            if resp.get('x-github-otp', '').startswith('required'):
                print("Two-Factor Authentication required.")
                resp, content = httplib2.Http().request(
                    url,
                    'POST',
                    headers=self._auth_header(use_otp=True),
                    body=json.dumps(body_dict))

        return resp, content

    def create_webhook(self, trigger_uri, workflow=None):
        hook_url = ('https://api.github.com/repos/%s/hooks' %
                    self.full_repo_name)
        if workflow is not None:
            wf_query = "?workflow=%s" % '+'.join(workflow)
            trigger_uri += wf_query
        hook_info = {
            'name': 'web',
            'events': ['pull_request', 'commit_comment'],
            'config': {
                'content_type': 'json',
                'url': trigger_uri,
            }
        }
        resp, content = self._send_authed_request(hook_url, hook_info)
        if resp.get('status') not in ['200', '201']:
            print("Error creating webhook.")

    def add_ssh_key(self, public_key=None, is_private=False):
        if not public_key:
            print("No public key to upload.")
            return
        if is_private:
            print("Uploading public key to user account.")
        else:
            print("Uploading public key to repository.")
        api_url = ('https://api.github.com/repos/%s/keys' %
                   self.full_repo_name)
        if is_private:
            api_url = 'https://api.github.com/user/keys'
        key_info = {
            'title': 'devops@Solum',
            'key': public_key,
            }

        resp, content = self._send_authed_request(api_url, key_info)
        if resp.get('status') not in ['200', '201']:
            print("Error uploading public key.")
