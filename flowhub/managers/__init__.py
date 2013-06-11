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
from collections import namedtuple

TagInfo = namedtuple("TagInfo", ["label", "message"])


class Manager(object):

    def __init__(
        self,
        debug,
        prefix,
        origin,
        canon,
        master,
        develop,
        release,
        hotfix,
        repo,
        gh,
        offline
    ):
        self._prefix = prefix
        self.DEBUG = debug
        self.origin = origin
        self.canon = canon
        self.master = master
        self.develop = develop
        self.release = release
        self.hotfix = hotfix
        self.repo = repo
        self.gh = gh
        self.offline = offline


