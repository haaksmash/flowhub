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

from managers import Manager

class FeatureManager(Manager):

    def start(self, name, with_tracking=False, summary=None):
        if summary is None:
            summary = []

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
            if self.__debug > 0:
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


