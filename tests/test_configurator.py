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

import git
import mock
import os
from unittest import TestCase

from flowhub.configurator import Configurator, DuplicateSectionError, Section
from tests import TEST_REPO
from tests import id_generator


class SectionTestCase(TestCase):
    def do_set_up(self, **kwargs):
        self.mock_configurator = mock.MagicMock()
        self.section = Section(
            kwargs.get('name', id_generator()),
            self.mock_configurator,
            kwargs.get('read_only', False),
            kwargs.get('parent', None),
        )


class SectionWriteEnabledTestCase(SectionTestCase):
    def setUp(self):
        self.do_set_up()

    def test_initialize(self):
        pass

    def test_add_section(self):
        section_name = id_generator()
        new_section = self.section.add_section(section_name)

        self.assertEqual(
            new_section._parent, self.section
        )

        self.assertIn(
            new_section._name,
            self.section._subsections,
        )
        self.assertEqual(
            self.section._subsections.get(section_name),
            new_section,
        )

    def test_add_dup_section(self):
        section_name = id_generator()
        self.section.add_section(section_name)

        with self.assertRaises(DuplicateSectionError):
            self.section.add_section(section_name)

    def test_set_value(self):
        value_name = id_generator()
        value = id_generator()

        self.assertFalse(hasattr(self.section, value_name))

        self.section.set_value(value_name, value)

        self.assertTrue(hasattr(self.section, value_name))
        self.assertEqual(getattr(self.section, value_name), value)

        self.mock_configurator.assert_has_calls([
            mock.call._confer.set(self.section._name, value_name, value),
            mock.call._confer.write()
        ])

    def test_set_value_dot_syntax(self):
        value_name = id_generator()
        value = id_generator()
        self.section.set_value(value_name, value)

        new_value = "NEW" + str(value)
        setattr(self.section, value_name, new_value)

        self.assertEqual(getattr(self.section, value_name), new_value)

    def test_invalid_subsection_overwrite(self):
        value = id_generator()
        section_name = id_generator()
        self.section.add_section(section_name)

        with self.assertRaises(RuntimeError):
            setattr(self.section, section_name, value)


class SectionWriteDisabledTestCase(SectionTestCase):
    def setUp(self):
        self.do_set_up(read_only=True)

    def test_initialization(self):
        pass

    def test_set_value(self):
        value_name = id_generator()
        value = id_generator()

        with self.assertRaises(AttributeError):
            self.section.set_value(value_name, value)


class ConfiguratorTestCase(TestCase):
    def setUp(self):
        print "Creating new test repo..."
        self.repo = git.Repo.init(TEST_REPO)
        # make an initial commit
        self.repo.index.commit("Initial commit")
        os.chdir(TEST_REPO)

        self._setup_configurator()

    def _setup_configurator(self, **kwargs):
        self.sections = [
            "core",
            "flowhub \"auth\"",
            "flowhub \"structure\"",
        ]
        self.mock_config = mock.MagicMock(
            read_only=kwargs.get('read_only', False),
            sections=lambda: self.sections,
        )
        self.configurator = Configurator(self.mock_config)

    def _test_basic_sections(self, configurator):

        self.assertTrue(hasattr(configurator, 'core'))
        self.assertTrue(hasattr(configurator, 'flowhub'))
        self.assertTrue(hasattr(configurator.flowhub, 'auth'))
        self.assertTrue(hasattr(configurator.flowhub, 'structure'))


class ConfiguratorInitializationTestCase(ConfiguratorTestCase):

    def test_reader_init(self):
        self._test_basic_sections(self.configurator)

    def test_writer_init(self):
        self._test_basic_sections(self.configurator)


class ConfiguratorAddSectionTestCase(ConfiguratorTestCase):
    def test_add_section(self):
        section_name = id_generator()

        self.configurator.add_section(section_name)

        self.assertTrue(hasattr(self.configurator, section_name))
        self.mock_config.assert_has_calls([
            mock.call.add_section(section_name),
        ])

    def test_add_section_with_subsection(self):
        section_name = id_generator()
        subsection_name = id_generator()

        section_whole_name = "{} \"{}\"".format(section_name, subsection_name)
        self.configurator.add_section(section_whole_name)

        self.assertTrue(hasattr(self.configurator, section_name))
        self.assertTrue(hasattr(getattr(self.configurator, section_name), subsection_name))

    def test_add_duplicate_section(self):
        section_name = id_generator()

        self.configurator.add_section(section_name)
        self.configurator.add_section(section_name)
