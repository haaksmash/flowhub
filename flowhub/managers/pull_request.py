"""
Copyright (C) 2012 Haak Saxberg

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

import re

from github import GithubException

from flowhub.managers import Manager


def sanitize_refs(method):
    def wrapper(self, base, head, *args, **kwargs):
        if self.canon != self.origin:
            head = "{}:{}".format(self.gh.get_user().login, head)

        return method(self, base, head, *args, **kwargs)
    return wrapper


class PullRequestManager(Manager):

    def __init__(self, *args, **kwargs):
        super(PullRequestManager, self).__init__(*args, **kwargs)

        if self.offline:
            self.gh_repo = None

        else:
            if self.canon == self.origin:
                self.gh_repo = self.gh.get_user().get_repo(self._prefix)
            else:
                self.gh_repo = self.gh.get_user().get_repo(self._prefix).parent

    @sanitize_refs
    def create_from_branch_name(self, base, head, summary):

        if self.DEBUG > 1:
            print "setting up new pull-request"

        component_name = head.name.split('/')[-1]

        # check for issue-numbers at the front of the branch name
        # if there is one, attach the pull-request to that issue.
        match = re.match('^\d+', component_name)
        if match:
            issue_number = match.group()
            issue = self.gh_repo.get_issue(int(issue_number))
            pr = self.gh_repo.create_pull(
                issue=issue,
                base=base.name,
                head=head.name,
            )
            summary += [
                "New pull request created: {} into {}"
                "\n\turl: {}".format(
                    head,
                    base,
                    pr.issue_url,
                )
            ]
            return pr

        return False

    @sanitize_refs
    def create_pull(self, base, head, issue, summary):
        pr = self.gh_repo.create_pull(
            issue=issue,
            base=base.name,
            head=head.name,
        )

        summary += [
            "New pull request created: {} into {}"
            "\n\turl: {}".format(
                head,
                base,
                pr.issue_url,
            )
        ]

        return pr

    @sanitize_refs
    def add_to_pull(self, base, head, summary):
        if self.offline:
            return False

        prs = [
            x for x in self.gh_repo.get_pulls('open')
            if x.head.label == head
            or x.head.label == "{}:{}".format(self.gh.get_user().login, head)
        ]

        # If there's already a pull-request, don't bother hitting the gh api.
        if prs:
            pr = prs[0]
            summary += [
                "New commits added to existing pull-request"
                "\n\turl: {}".format(pr.issue_url)
            ]
            return pr

        else:
            return False

    def get_issue(self, issue_num):
        try:
            return self.gh_repo.get_issue(issue_num)
        except GithubException:
            return None

    def open_issue(self, title, body, labels, summary):
        gh_labels = [l for l in self.gh_repo.get_labels() if l.name in labels]

        issue = self.gh_repo.create_issue(
            title=title,
            body=body or "No description provided.",
            labels=gh_labels,
        )

        summary += [
            'Opened issue #{}: {}{}\n'
            '\turl: {}'.format(
                issue.number,
                title,
                '\n\t[{}]'.format(' '.join([l.name for l in gh_labels])) if gh_labels else '',
                issue.url,
            )
        ]

        return issue
