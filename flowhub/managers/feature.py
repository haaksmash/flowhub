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

from flowhub.managers import Manager


class FeatureManager(Manager):

    def start(self, name, with_tracking, summary):
        branch_name = "{}{}".format(
            self._prefix,
            name,
        )
        branch = self.repo.create_head(
            branch_name,
            commit=self.develop,  # Requires a develop branch.
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self.develop,
            )
        ]

        # can't create a tracking branch if we're offline
        if not self.offline and with_tracking:
            if self.DEBUG > 0:
                print "Adding a tracking branch to your GitHub repo"

            self.repo.git.push(
                self.origin,
                branch_name,
                set_upstream=True
            )

            summary += [
                "Created a remote tracking branch on {} for {}".format(
                    self.origin.name,
                    branch_name,
                ),
            ]

        return branch

    def get(self, name):
        try:
            return getattr(self.repo.branches, "{}{}".format(self._prefix, name))
        except AttributeError:
            return None

    def fuzzy_get(self, name):
        branch_name = "{}{}".format(
            self._prefix,
            name
        )

        try:
            branches = [getattr(self.repo.branches, branch_name)]
        except AttributeError:
            branches = [b for b in self.repo.branches if b.startswith(branch_name)]

        return branches

    def accept(self, name, summary, with_delete):
        self.canon.fetch()
        summary += [
            "Latest objects fetched from {}".format(self.canon),
        ]
        self.develop.checkout()
        self.repo.git.merge(
            "{}/{}".format(self.canon, self.develop),
        )
        summary += [
            "Updated {}".format(self.develop),
        ]

        branch_name = "{}{}".format(
            self._prefix,
            name,
        )

        if with_delete:
            self.repo.delete_head(
                branch_name,
            )
            summary += [
                "Deleted {} from local repository".format(branch_name),
            ]

            if not self.offline:
                self.origin.push(
                    branch_name,
                    delete=True,
                )
                summary += [
                    "Deleted {} from {}".format(branch_name, self.origin),
                ]

    def abandon(self, name, summary):
        branch_name = "{}{}".format(
            self._prefix,
            name,
        )

        self.repo.delete_head(
            branch_name,
            force=True,
        )
        summary += [
            "Deleted branch {} locally".format(
                branch_name,
            ),
        ]

        if not self.offline:
            self.repo.git.push(
                self.origin,
                branch_name,
                delete=True,
                force=True,
            )
            summary[-1] += "and from remote {}".format(
                self.origin,
            )

    def publish(self, name, summary):
        branch_name = "{}{}".format(
            self._prefix,
            name,
        )
        self.repo.git.push(
            self.origin,
            branch_name,
            set_upstream=True,
        )
        summary += [
            "Updated {}/{}".format(self.origin, branch_name)
        ]

        return self.get(name)
