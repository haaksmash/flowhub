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
from flowhub.connectors.results import RequestResult


class NoopConnector(object):
    def __init__(self, config):
        pass

    def make_request(self, **kwargs):
        return RequestResult(False, None, False)

    def service_name(self):
        return "NoOp"

    def is_authorized(self):
        return True

    def get_authorization(self, output_func, input_func):
        return None
