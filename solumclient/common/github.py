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
import six


class GitHubException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

    def __str__(self):
        return "GitHub Exception: %s: %s" % (self.status_code, self.message)


class GitHubAuth(object):
    _github_auth_url = 'https://api.github.com/authorizations'
    _github_repo_hook_url = 'https://api.github.com/repos/%s/hooks'
    _github_user_key_url = 'https://api.github.com/user/keys'
    _github_repo_regex = r'github\.com[:/](.+?)/(.+?)($|/$|\.git$|\.git/$)'

    def __init__(self, git_url, username=None, password=None, repo_token=None):
        self.git_url = git_url

        user_org_name, repo = '', ''

        repo_pat = re.compile(self._github_repo_regex)
        match = repo_pat.search(self.git_url)
        if match:
            user_org_name, repo = match.group(1), match.group(2)
        else:
            raise ValueError("Failed to parse %s." % git_url)

        self.user_org_name = user_org_name

        self.full_repo_name = '/'.join([user_org_name, repo])

        self._repo_token = repo_token
        self._username = username
        self._password = password
        self._otp_required = False

    @property
    def username(self):
        if self._username is None:
            prompt = ("Username for repo '%s' [%s]:" %
                      (self.full_repo_name, self.user_org_name))
            self._username = six.moves.input(prompt) or self.user_org_name
        return self._username

    @property
    def password(self):
        if self._password is None:
            self._password = getpass.getpass("Password: ")
        return self._password

    @property
    def onetime_password(self):
        # This is prompted for every time it's needed.
        print("Two-Factor Authentication required.")
        return getpass.getpass("2FA Token: ")

    @property
    def repo_token(self):
        if self._repo_token is None:
            self.create_repo_token()
        return self._repo_token

    @property
    def auth_header(self):
        header = {
            'Content-Type': 'application/json',
            }

        # The token on its own should suffice
        if self._repo_token:
            header['Authorization'] = 'token %s' % self._repo_token
            return header

        # This will prompt the user if either name or pass is missing.
        authstring = '%s:%s' % (self.username, self.password)
        basic_auth = ''
        try:
            basic_auth = base64.encodestring(authstring)
        except TypeError:
            # Python 3
            basic_auth = base64.encodestring(bytes(authstring, 'utf-8'))
            basic_auth = basic_auth.decode('utf-8')
        basic_auth = basic_auth.strip()
        header['Authorization'] = 'Basic %s' % basic_auth

        # This will prompt for the OTP.
        if self._otp_required:
            header['x-github-otp'] = self.onetime_password

        return header

    def _send_authed_request(self, url, body_dict):
        body_text = json.dumps(body_dict)

        resp, content = httplib2.Http().request(
            url, 'POST',
            headers=self.auth_header,
            body=body_text)

        if resp.get('status') in ['401']:
            if resp.get('x-github-otp', '').startswith('required'):
                self._otp_required = True
                resp, content = httplib2.Http().request(
                    url, 'POST',
                    headers=self.auth_header,
                    body=body_text)

        return resp, content

    def create_repo_token(self):
        print("Creating repo token")
        note = ''.join(random.sample(string.lowercase, 5))
        auth_info = {
            'scopes': ['repo', 'write:public_key', 'write:repo_hook'],
            'note': 'Solum-status-%s' % note,
            }

        resp, content = self._send_authed_request(
            self._github_auth_url,
            auth_info)

        status_code = int(resp.get('status', '500'))
        response_body = json.loads(content)
        if status_code in [200, 201]:
            self._repo_token = response_body.get('token')
            print("Successfully created repo token %s." % auth_info['note'])
            return self._repo_token
        elif status_code >= 400 and status_code < 600:
            message = response_body.get('message',
                                        'No error message provided.')
            raise GitHubException(status_code, message)

    def create_webhook(self, trigger_uri, workflow=None):
        print("Creating webhook for repo.")
        hook_url = self._github_repo_hook_url % self.full_repo_name
        if workflow is not None:
            # workflow is a list of strings, likely
            # ['unittest', 'build', 'deploy'].
            # They're joined with + and appended to the
            # trigger_uri here.
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
        if resp.get('status') in ['200', '201']:
            print("Successfully created webhook.")
        else:
            print("Error creating webhook.")

    def add_ssh_key(self, public_key=None):
        if not public_key:
            print("No public key to upload.")
            return
        print("Uploading public key to user account.")
        api_url = self._github_user_key_url

        key_info = {
            'title': 'devops@Solum',
            'key': public_key,
            }

        resp, content = self._send_authed_request(api_url, key_info)
        if resp.get('status') in ['200', '201']:
            print("Successfully uploaded public key.")
        else:
            print("Error uploading public key.")
