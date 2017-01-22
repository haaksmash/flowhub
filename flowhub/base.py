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
import textwrap

from flowhub.utilities import future_proof_print


class Base(object):
    def print_at_verbosity(self, msgs):
        verbosity = getattr(self, '_verbosity', 0)
        possible_msg_keys = filter(lambda k: k <= verbosity, sorted(msgs.keys()))
        if len(possible_msg_keys) < 1:
            return None

        msg_key = possible_msg_keys[-1]
        msg = msgs[msg_key]

        output_func = getattr(self, '_output', future_proof_print)
        output_func(textwrap.dedent(msg))
