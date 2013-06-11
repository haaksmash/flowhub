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

from flowhub.managers import Manager


class HotfixManager(Manager):

    def start(self, name, issues, summary):
        branch_name = "{}{}{}".format(
            self._prefix,
            "-".join(['{}'.format(issue) for issue in issues]) + '-' if issues is not None else "",
            name,
        )

        if not self.offline:
            self.canon.fetch()

        summary += [
            "Latest objects fetched from {}".format(self.canon),
        ]
        self.master.checkout()
        self.repo.git.merge(
            "{}/{}".format(self.canon, self.master),
        )
        summary += [
            "Updated {}".format(self.master),
        ]

        branch = self.repo.create_head(
            branch_name,
            commit=self.master,
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch,
                self.master,
            ),
        ]

        if self.DEBUG > 0:
            print "Adding a tracking branch to your GitHub repo"
        if not self.offline:
            self.canon.push(
                "{0}:{0}".format(branch),
                set_upstream=True,
            )
            summary += [
                "Pushed {} to {}".format(branch, self.canon),
            ]

        return branch  # getattr(self._repo.branches, branch_name)

    def publish(self, name, tag_info, with_delete, summary):
        if self.offline:
            return False

        hotfix_name = "{}{}".format(
            self._prefix,
            name,
        )

        self.canon.fetch()
        summary += [
            "Latest objects fetched from {}".format(self.canon),
        ]

        # TODO: ensure equality of remote and local master/develop branches
        # TODO: handle merge conflicts.
        # merge into master
        self.master.checkout()
        self.repo.git.merge(
            hotfix_name,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(hotfix_name, self.master),
        ]

        # and tag
        issue_numbers = re.findall('(\d+)-', name)
        # cut off any issue numbers that may be there

        self.repo.create_tag(
            path=tag_info.label,
            ref=self.master,
            message=tag_info.message,
        )
        summary += [
            "New tag ({}) created at {}'s tip".format(tag_info.label, self.master),
        ]

        # merge into develop (or release, if exists)
        if self.release:
            trunk = self.release
        else:
            trunk = self.develop

        trunk.checkout()
        self.repo.git.merge(
            self.master,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(self.master, trunk),
        ]

        # push to canon
        self.canon.push()
        self.canon.push(tags=True)
        summary += [
            "{}, {}, and tags have been pushed to {}".format(self.master, trunk, self.canon),
        ]

        for number in issue_numbers:
            try:
                number = int(number)
            except ValueError:
                continue

            issue = self.gh.get_issue(number)
            issue.edit(state='closed')
            summary += [
                "Closed issue #{}".format(issue.number),
            ]

        if with_delete:
            self.repo.delete_head(hotfix_name)
            self.canon.push(
                hotfix_name,
                delete=True,
            )
            summary += [
                "Branch {} removed".format(hotfix_name),
            ]
        return True

    def contribute(self, branch, summary):
        self.repo.git.push(
            self.origin,
            branch,
            set_upstream=True,
        )
        summary += [
            "Branch {} pushed to {}".format(branch, self.origin)
        ]

        return True
