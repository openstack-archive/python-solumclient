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
    fake_username = 'fakeuser'
    fake_password = 'fakepassword'

    def test_invalid_repo(self):
        self.assertRaises(ValueError,
                          github.GitHubAuth,
                          "http://example.com")

    def test_token_fetched_on_request(self):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        gha._get_repo_token = mock.Mock()
        gha.token
        gha._get_repo_token.assert_called_once()

    def test_token_fetched_only_once(self):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)

        def update_token(some_gha):
            some_gha._token = 'foo'
        gha._get_repo_token = mock.Mock(side_effect=update_token(gha))
        for i in range(5):
            gha.token
        gha._get_repo_token.assert_called_once()
        self.assertEqual(gha.token, 'foo')

    @mock.patch('httplib2.Http.request')
    def test_create_webhook(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "foo"}')
        fake_trigger_url = 'http://example.com'
        gha.create_webhook(fake_trigger_url)
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/hooks',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {
            "config": {
                "url": fake_trigger_url,
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
        fake_trigger_url = 'http://example.com'
        gha.create_webhook(fake_trigger_url, workflow=['unittest'])
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/hooks',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {
            "config": {
                "url": fake_trigger_url + "?workflow=unittest",
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
        fake_trigger_url = 'http://example.com'
        gha.create_webhook(fake_trigger_url, workflow=['unittest', 'build'])
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/hooks',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {
            "config": {
                "url": fake_trigger_url + "?workflow=unittest+build",
                "content_type": "json"},
            "name": "web",
            "events": ["pull_request", "commit_comment"]}
        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)

    @mock.patch('httplib2.Http.request')
    def test_add_ssh_key_public(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "foo"}')
        fake_pub_key = 'foo'
        gha.add_ssh_key(public_key=fake_pub_key)
        fake_request.assert_called_once_with(
            'https://api.github.com/repos/fakeuser/fakerepo/keys',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {"key": "foo", "title": "devops@Solum"}
        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)

    @mock.patch('httplib2.Http.request')
    def test_add_ssh_key_private(self, fake_request):
        gha = github.GitHubAuth(self.fake_repo,
                                username=self.fake_username,
                                password=self.fake_password)
        fake_request.return_value = ({'status': '200'},
                                     '{"token": "foo"}')
        fake_pub_key = 'foo'
        gha.add_ssh_key(public_key=fake_pub_key, is_private=True)
        fake_request.assert_called_once_with(
            'https://api.github.com/user/keys',
            'POST',
            headers=mock.ANY,
            body=mock.ANY)
        expected_body = {"key": "foo", "title": "devops@Solum"}
        actual_body = json.loads(fake_request.call_args[1]['body'])
        self.assertEqual(expected_body, actual_body)
