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

from contextlib import contextmanager
import re


class Configurator(object):
    def __init__(self, repo):
        self._repo = repo

    @contextmanager
    def reader(self):
        reader = self._repo.config_reader()
        yield Sections(reader)

    @contextmanager
    def writer(self):
        with self._repo.config_writer() as writer:
            yield writer


class Sections(object):
    def __init__(self, reader):
        self._reader = reader
        self._sections = {}

        self._build_config_tree()

    def _build_config_tree(self):
        for section_name in self._reader.sections():
            match = re.match('(?P<section>.+) "(?P<subsection>.+)"$', section_name)
            if match:
                supersection_name = match.groupdict()['section']
                actual_section_name = match.groupdict()['subsection']

                # this may or may not be the first time we've seen this
                # supersection:
                #     [flowhub "structure"]
                #     [flowhub "prefix"]
                # but 'structure' and 'prefix' both need to nest under the same
                # 'flowhub'.
                supersection = self._sections.setdefault(
                    supersection_name,
                    Section(supersection_name),
                )

                section = supersection.add_section(actual_section_name)
            else:
                section = self._sections.setdefault(section_name, Section(section_name))

            for name, value in self._reader._sections[section_name].iteritems():
                section.set_value(name, value)

    def __getattr__(self, attr_name):
        sections = super(Sections, self).__getattribute__('_sections')
        if attr_name in sections:
            return sections[attr_name]

        return super(Sections, self).__getattribute__(attr_name)


class Section(object):
    def __init__(self, name):
        self._name = name
        self._subsections = {}
        self._values = {}

    def __getattr__(self, attr_name):
        subsections = super(Section, self).__getattribute__('_subsections')
        values = super(Section, self).__getattribute__('_values')
        if attr_name in subsections:
            return subsections[attr_name]

        if attr_name in values:
            return values[attr_name]

        try:
            return super(Section, self).__getattribute__(attr_name)
        except AttributeError:
            return None

    def add_section(self, name):
        return self._subsections.setdefault(name, Section(name))

    def set_value(self, name, value):
        self._values[name] = value
