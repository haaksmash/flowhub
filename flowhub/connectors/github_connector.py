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
import re
import subprocess
import textwrap
import traceback

from github import Github, GithubException
from github.GithubException import TwoFactorException

from flowhub.exceptions import Abort
from flowhub.connectors.results import IssueResult, RequestResult


class GithubConnector(object):
    def __init__(self, config, engine):
        self._config = config
        self._engine = engine

    @property
    def github(self):
        if getattr(self, '_github', None):
            return self._github
        with self._config.reader() as reader:
            token = reader.flowhub.auth.token
        self._github = Github(token)
        return self._github

    @property
    def gh_repo(self):
        with self._config.reader() as reader:
            repo_name = reader.flowhub.structure.name
        repo = self.github.get_user().get_repo(repo_name)
        return repo

    @property
    def canon_repo(self):
        repo = self.gh_repo
        with self._config.reader() as reader:
            if reader.flowhub.structure.canon != reader.flowhub.structure.origin:
                repo = repo.parent
        return repo

    def make_request(self, base_branch_name, branch_name, remote_name):
        existing_pull = self._add_to_pulls(base_branch_name, branch_name)
        if existing_pull is not None:
            return RequestResult(True, existing_pull.html_url, False)

        new_pull = self._create_pull_request(base_branch_name, branch_name)
        if new_pull is not None:
            return RequestResult(True, new_pull.html_url, True)

        return RequestResult(False, 'https://github.com', False)

    def close_request(self, branch_name):
        if self.__close_gh_pull_request(branch_name):
            return RequestResult(True, 'https://github.com', False)

        return RequestResult(False, 'https://github.com', False)

    def open_issue(self, title, body, labels):
        labels = [l for l in self.canon_repo.get_labels() if l.name in labels]
        if body is None:
            body = "No description provided."

        issue = self.canon_repo.create_issue(
            title=title,
            body=body,
            labels=labels,
        )

        return IssueResult(True, issue.html_url, issue.number)

    def service_name(self):
        return 'GitHub'

    def is_authorized(self):
        with self._config.reader() as reader:
            if reader.flowhub.auth is None:
                return False
            return reader.flowhub.auth.token is not None

    def get_authorization(self):
        self._engine.request_output(textwrap.dedent("""
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
            self._engine.request_output("  {}. {}".format(i + 1, step))
        token = self._engine.request_input("  {}. Enter the token here: ".format(len(steps) + 1))

        # set the token globally, rather than on the repo level.
        subprocess.check_output(
            'git config --global --add flowhub.auth.token {}'.format(token),
            shell=True,
        ).strip()

        self._engine.request_output("""
        ...
        ...
        ...great! We're all set. You can rest assured that Flowhub isn't
        storing your credentials somewhere, because we didn't ask for them!""")

        return None

    def _normalized_branch_name(self, local_branch_name):
        with self._config.reader() as reader:
            if reader.flowhub.structure.canon != reader.flowhub.structure.origin:
                return self._canonical_branch_name(local_branch_name)
            else:
                return local_branch_name

    def _canonical_branch_name(self, local_branch_name):
        return "{}:{}".format(self.github.get_user().login, local_branch_name)


    def _add_to_pulls(self, base_branch_name, branch_name):
        pull_requests = [
            x for x in self.canon_repo.get_pulls('open')
            if x.head.label == self._canonical_branch_name(branch_name)
        ]

        if len(pull_requests) > 0:
            pull_request = pull_requests[0]
            return pull_request

        return None

    def _create_pull_request(self, base_branch_name, local_branch_name):
        # check for issue number at the start of the local branch name
        prefix = self._engine.get_prefixes()['feature']
        match = re.match('^\d+', local_branch_name.replace(prefix, ''))
        if match:
            issue_number = int(match.group())
            issue = self.canon_repo.get_issue(issue_number)
            pull_request = self.__create_gh_pull_request(
                issue,
                base_branch_name,
                local_branch_name,
            )

            return pull_request

        is_issue = self._engine.request_input('Is this feature answering an issue? [y/N] ')
        if not is_issue:
            result = self._engine.create_issue()
            with self._config.writer() as writer:
                writer.set('branch "{}"'.format(local_branch_name), 'githubIssueNumber', result.number)

            issue = self.canon_repo.get_issue(result.number)
            pull_request = self.__create_gh_pull_request(
                issue,
                base_branch_name,
                local_branch_name,
            )
            return pull_request
        else:
            good_number = False
            while not good_number:
                try:
                    issue_number = int(self._engine.request_input("Issue #: "))
                    issue = self._get_issue(issue_number)
                except (ValueError, GithubException):
                    self._engine.request_output("Please enter a valid issue number.")
                    continue

                good_number = True

            pull_request = self.__create_gh_pull_request(
                issue,
                base_branch_name,
                local_branch_name,
            )

            return pull_request

        return None

    def __create_gh_pull_request(
        self,
        issue,
        base_branch_name,
        local_branch_name,
    ):
        pull_request = self.canon_repo.create_pull(
            issue=issue,
            base=base_branch_name,
            head=local_branch_name,
        )

        return pull_request

    def __close_gh_pull_request(self, branch_name):
        return True

    def _create_issue(self, title, labels):
        pass

    def _get_issue(self, issue_number):
        try:
            return self.canon_repo.get_issue(issue_number)
        except:
            return None
