"""
Copyright (C) 2017 Haak Saxberg

This file is part of Flowhub, a command-line tool to enable various
Git-based workflows that interacts with GitHub.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import getpass
import subprocess
import textwrap
import traceback

from github import Github, GithubException
from github.GithubException import TwoFactorException

from flowhub.exceptions import Abort
from flowhub.connectors.results import RequestResult


class GithubConnector(object):
    def __init__(self, config):
        self._config = config

    @property
    def github(self):
        if self._github:
            return self._github
        with self._config.reader() as reader:
            token = reader.flowhub.auth.token
        self._github = GitHub(token)
        return self._github

    def make_request(self, base_branch_name, branch_name, remote_name):
        return RequestResult(True, 'https://github.com', False)

    def service_name(self):
        return 'GitHub'

    def is_authorized(self):
        with self._config.reader() as reader:
            if reader.flowhub.auth is None:
                return False
            return reader.flowhub.auth.token is not None

    def get_authorization(self, output_func, input_func):
        output_func(textwrap.dedent("""
        Flowhub needs permission to access your Github repositories.
        Entering a personal authorization token will grant Flowhub the access
        it requires!

        To generate an authorization token, do the following (don't worry;
        you'll only have to do this once):"""))
        steps = [
            "Go to https://github.com/settings/tokens",
            "Generate a new token",
            "Check the 'repo' set of permissions (Flowhub needs all of them)",
            "Generate the token",
        ]

        for i, step in enumerate(steps):
            output_func("  {}. {}".format(i + 1, step))
        token = input_func("  {}. Enter the token here: ".format(len(steps) + 1))

        # set the token globally, rather than on the repo level.
        subprocess.check_output(
            'git config --global --add flowhub.auth.token {}'.format(token),
            shell=True,
        ).strip()

        output_func("""
        ...
        ...
        ...great! We're all set. You can rest assured that Flowhub isn't
        storing your credentials somewhere, because we didn't ask for them!""")

        return None
