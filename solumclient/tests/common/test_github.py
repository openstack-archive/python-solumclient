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

import json

import mock

from solumclient.common import github
from solumclient.tests import base


class TestGitHubAuth(base.TestCase):
    fake_repo = "http://github.com/fakeuser/fakerepo.git"
    fake_trigger = "http://example.com/trigger/1"
    fake_username = 'fakeuser'
    fake_password = 'fakepassword'
    fake_token = 'faketoken'

    def test_invalid_repo(self):
        self.assertRaises(ValueError,
                          github.GitHubAuth,
                          "http://example.com")

    def test_auth_header_username_password(self):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        # base64.b64encode('fakeuser:fakepassword') yields 'ZmFrZX...'
        expected_auth_header = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ZmFrZXVzZXI6ZmFrZXBhc3N3b3Jk',
        }
        self.assertEqual(expected_auth_header, gha.auth_header)

    @mock.patch('getpass.getpass')
    def test_auth_header_username_password_2fa(self, fake_getpass):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        gha._otp_required = True
        fake_getpass.return_value = 'fakeonetime'
        expected_auth_header = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ZmFrZXVzZXI6ZmFrZXBhc3N3b3Jk',
            'x-github-otp': 'fakeonetime',
        }
        self.assertEqual(expected_auth_header, gha.auth_header)

    def test_auth_header_repo_token(self):
        gha = github.GitHubAuth(self.fake_repo,
                                repo_token=self.fake_token)
        expected_auth_header = {
            'Content-Type': 'application/json',
            'Authorization': 'token %s' % self.fake_token,
        }
        self.assertEqual(expected_auth_header, gha.auth_header)

    @mock.patch('httplib2.Http.request')
    def test_create_webhook(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                repo_token=self.fake_token)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "%s"}' % self.fake_token)
        gha.create_repo_token = mock.MagicMock()
        gha.create_repo_token.return_value = 'token123'

        gha.create_webhook(self.fake_trigger)
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/hooks',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)

        expected_body = {
            "config": {
                "url": self.fake_trigger,
                "content_type": "json"},
            "name": "web",
            "events": ["pull_request", "commit_comment"]}

        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)

    @mock.patch('httplib2.Http.request')
    def test_create_webhook_unittest_only(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "foo"}')

        gha.create_repo_token = mock.MagicMock()
        gha.create_repo_token.return_value = 'token123'

        gha.create_webhook(self.fake_trigger, workflow=['unittest'])
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/hooks',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {
            "config": {
                "url": self.fake_trigger + "?workflow=unittest",
                "content_type": "json"},
            "name": "web",
            "events": ["pull_request", "commit_comment"]}
        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)

    @mock.patch('httplib2.Http.request')
    def test_create_webhook_unittest_build(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "foo"}')

        gha.create_repo_token = mock.MagicMock()
        gha.create_repo_token.return_value = 'token123'

        gha.create_webhook(self.fake_trigger, workflow=['unittest', 'build'])
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/hooks',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {
            "config": {
                "url": self.fake_trigger + "?workflow=unittest+build",
                "content_type": "json"},
            "name": "web",
            "events": ["pull_request", "commit_comment"]}
        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)

    @mock.patch('httplib2.Http.request')
    def test_add_ssh_key(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "foo"}')
        fake_pub_key = 'foo'
        gha.add_ssh_key(public_key=fake_pub_key)
        fake_request.assert_called_once_with(
            'https://api.github.com/user/keys',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {"key": "foo", "title": "devops@Solum"}
        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)
