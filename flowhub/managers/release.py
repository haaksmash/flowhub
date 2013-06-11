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


class ReleaseManager(Manager):

    def start(self, name, summary):
        # checkout develop
        # checkout -b release/name

        branch_name = "{}{}".format(
            self._prefix,
            name,
        )
        branch = self.repo.create_head(
            branch_name,
            commit=self.develop,
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self.develop,
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
                "Pushed {} to {}".format(branch, self.canon.name),
            ]

        return branch

    def publish(self, name, with_delete, tag_info, summary):
        if self.offline:
            return False
        release_name = "{}{}".format(
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
            release_name,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(release_name, self.master),
        ]

        # and tag
        if tag_info:
            self.repo.create_tag(
                path=tag_info.label,
                ref=self.master,
                message=tag_info.message,
            )
            summary += [
                "New tag ({}) created at {}'s tip".format(tag_info.label, self.master),
            ]

        # merge into develop
        self.develop.checkout()
        self.repo.git.merge(
            self.master,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(self.master, self.develop),
        ]

        # push to canon
        self.canon.push()
        self.canon.push(tags=True)
        summary += [
            "{}, {}, and tags have been pushed to {}".format(
                self.master,
                self.develop,
                self.canon
            ),
        ]

        if with_delete:
            self.repo.delete_head(release_name)
            self.canon.push(
                release_name,
                delete=True,
            )
            summary += [
                "Branch {} removed".format(release_name),
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
