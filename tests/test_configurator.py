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
import pytest
import os

from flowhub.configurator import Configurator, DuplicateSectionError, Section


@pytest.fixture
def configurator():
    return mock.MagicMock(spec=Configurator)


@pytest.fixture
def section(configurator, id_generator):
    return Section(
        id_generator(),
        configurator,
        False,
        None,
    )


class SectionWriteEnabledTestCase(object):

    def test_initialize(self, section):
        pass

    def test_add_section(self, section, id_generator):
        section_name = id_generator()
        new_section = section.add_section(section_name)

        assert new_section._parent == section

        assert new_section._name in section._subsections
        assert section._subsections.get(section_name) == new_section

    def test_add_dup_section(self, section, id_generator):
        section_name = id_generator()
        section.add_section(section_name)

        with pytest.raises(DuplicateSectionError):
            section.add_section(section_name)

    def test_set_value(self, section, configurator, id_generator):
        value_name = id_generator()
        value = id_generator()

        assert not hasattr(section, value_name)

        section.set_value(value_name, value)

        assert hasattr(section, value_name)
        assert getattr(section, value_name) is value

        configurator.assert_has_calls([
            mock.call._confer.set(section._name, value_name, value),
            mock.call._confer.write()
        ])

    def test_set_value_dot_syntax(self, section, id_generator):
        value_name = id_generator()
        value = id_generator()
        section.set_value(value_name, value)

        new_value = "NEW" + str(value)
        setattr(section, value_name, new_value)

        assert getattr(section, value_name) is new_value

    def test_invalid_subsection_overwrite(self, section, id_generator):
        value = id_generator()
        section_name = id_generator()
        section.add_section(section_name)

        with pytest.raises(RuntimeError):
            setattr(section, section_name, value)


class SectionWriteDisabledTestCase(object):

    @pytest.fixture
    def section(self, configurator, id_generator):
        return Section(
            id_generator(),
            configurator,
            True,
            None,
        )

    def test_initialization(self, section):
        pass

    def test_set_value(self, section, id_generator):
        value_name = id_generator()
        value = id_generator()

        with pytest.raises(AttributeError):
            section.set_value(value_name, value)


class ConfiguratorTestCase(object):

    @pytest.yield_fixture
    def repository(self, TEST_REPO):
        repo = git.Repo.init(TEST_REPO)
        repo.index.commit("Initial commit")
        os.chdir(TEST_REPO)
        yield repo
        os.rmdir(TEST_REPO)

    @pytest.fixture
    def sections(self):
        return [
            "core",
            'flowhub "auth"',
            'flowhub "structure"',
        ]

    @pytest.fixture
    def configurator(self, sections):
        mock_config = mock.MagicMock(
            read_only=False,
            sections=lambda: sections,
        )

        return Configurator(mock_config)

    def _test_basic_sections(self, configurator):

        assert hasattr(configurator, 'core')
        assert hasattr(configurator, 'flowhub')
        assert hasattr(configurator.flowhub, 'auth')
        assert hasattr(configurator.flowhub, 'structure')


class ConfiguratorInitializationTestCase(ConfiguratorTestCase):

    def test_reader_init(self, configurator):
        configurator._read_only = True
        self._test_basic_sections(configurator)

    def test_writer_init(self, configurator):
        self._test_basic_sections(configurator)


class ConfiguratorAddSectionTestCase(ConfiguratorTestCase):
    def test_add_section(self, configurator, id_generator):
        section_name = id_generator()

        configurator.add_section(section_name)

        assert hasattr(configurator, section_name)
        configurator._confer.assert_has_calls([
            mock.call.add_section(section_name),
        ])

    def test_add_section_with_subsection(self, configurator, id_generator):
        section_name = id_generator()
        subsection_name = id_generator()

        section_whole_name = "{} \"{}\"".format(section_name, subsection_name)
        configurator.add_section(section_whole_name)

        assert hasattr(configurator, section_name)
        assert hasattr(getattr(configurator, section_name), subsection_name)

    def test_add_duplicate_section(self, configurator, id_generator):
        section_name = id_generator()

        configurator.add_section(section_name)
        configurator.add_section(section_name)
