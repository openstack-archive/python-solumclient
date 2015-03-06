# Copyright 2013 - Noorul Islam K M
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from solumclient.openstack.common.apiclient import exceptions


class CommandException(Exception):
    """An error occurred."""
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.message or self.__class__.__doc__


class CommandError(CommandException):
    """Invalid usage of CLI."""


class NotUnique(CommandException):
    """Name refers to more than one of a given resource."""
    def __init__(self, resource='resource'):
        message = "More than one %s by that name. Retry with the UUID."
        self.message = message % resource


def from_response(response, method, url):
    """Returns an instance of :class:`HttpError` or subclass based on response.

    :param response: instance of `requests.Response` class
    :param method: HTTP method used for request
    :param url: URL used for request
    """
    kwargs = {
        "http_status": response.status_code,
        "response": response,
        "method": method,
        "url": url,
        "request_id": response.headers.get("x-compute-request-id"),
    }
    if "retry-after" in response.headers:
        kwargs["retry_after"] = response.headers["retry-after"]

    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith("application/json"):
        try:
            body = response.json()
        except ValueError:
            pass
        else:
            if isinstance(body, dict):
                kwargs["message"] = body.get("faultstring")
                kwargs["details"] = body.get("debuginfo")
    elif content_type.startswith("text/"):
        kwargs["details"] = response.text

    try:
        cls = exceptions._code_map[response.status_code]
    except KeyError:
        if 500 <= response.status_code < 600:
            cls = exceptions.HttpServerError
        elif 400 <= response.status_code < 500:
            cls = exceptions.HTTPClientError
        else:
            cls = exceptions.HttpError
    return cls(**kwargs)
