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

import functools


def with_summary(f):
    """Prints a nice summary, assuming the function accepts a
    'summary' kwarg and appends to it."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        summary = []
        r = f(*args, summary=summary, **kwargs)
        if summary:
            summary = ['\nSummary of actions:'] + summary
            print "\n - ".join(summary)

        else:
            print "No summary provided."

        return r

    return wrapper
