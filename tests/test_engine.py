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
import itertools
import mock
import os
import shutil
import string
import unittest

from tests import (
    id_generator,
    TEST_REPO,
    REPO_NAME,
)
from flowhub.engine import Engine, NoSuchBranch, NoSuchRemote


class NotARepoSetupTestCase(unittest.TestCase):
    def test_setup_abort(self):
        def raise_call_error(*args, **kwargs):
            raise git.exc.InvalidGitRepositoryError

        with mock.patch("git.Repo.__init__") as patch:
            patch.side_effect = raise_call_error

            with self.assertRaises(git.exc.InvalidGitRepositoryError):
                Engine(offline=True)


class EngineTestCase(unittest.TestCase):
    def setUp(self):
        self.gh_patch = mock.patch("flowhub.engine.Github")
        self.git_patch = mock.patch("git.Repo")
        self.configurator_patch = mock.patch("flowhub.engine.Configurator")

        self.gh_mock = self.gh_patch.start()
        self.git_mock = self.git_patch.start()
        self.configurator_mock = self.configurator_patch.start()

    def tearDown(self):
        super(EngineTestCase, self).tearDown()
        self.configurator_patch.stop()
        self.git_patch.stop()
        self.gh_patch.stop()


class OfflineTestCase(unittest.TestCase):
    def _produce_engine(self):
        engine = Engine(INIT=True, offline=True)

        self.repository_structure = {
            "name": id_generator(),
            "origin": id_generator(),
            "canon": id_generator(),
            "master": id_generator(),
            "develop": id_generator(),
            "feature": id_generator(),
            "release": id_generator(),
            "hotfix": id_generator(),
        }

        engine.setup_repository_structure(
            **self.repository_structure
        )

        # setup the configurator mock
        for key in ["origin", "canon", "master", "develop"]:
            setattr(
                self.configurator_mock().flowhub.structure,
                key,
                self.repository_structure[key]
            )
        for key in ["feature", "release", "hotfix"]:
            setattr(
                self.configurator_mock().flowhub.prefix,
                key,
                self.repository_structure[key]
            )

        self.engine = Engine(offline=True)
        self.feature_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['feature'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

    def tearDown(self):
        # ensure no Github accesses have happened
        self.assertEqual(self.gh_mock.call_count, 0)
        super(OfflineTestCase, self).tearDown()


class OnlineTestCase(unittest.TestCase):
    def _produce_engine(self):
        engine = Engine(INIT=True)

        self.repository_structure = {
            "name": id_generator(),
            "origin": id_generator(),
            "canon": id_generator(),
            "master": id_generator(),
            "develop": id_generator(),
            "feature": id_generator(),
            "release": id_generator(),
            "hotfix": id_generator(),
        }

        engine.setup_repository_structure(
            **self.repository_structure
        )

        # setup the configurator mock
        for key in ["origin", "canon", "master", "develop"]:
            setattr(
                self.configurator_mock().flowhub.structure,
                key,
                self.repository_structure[key]
            )
        for key in ["feature", "release", "hotfix"]:
            setattr(
                self.configurator_mock().flowhub.prefix,
                key,
                self.repository_structure[key]
            )

        self.engine = Engine()
        self.feature_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['feature'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                repo=mock.ANY,
                gh=self.gh_mock(),
                offline=False
            ),
        ])


class OfflineFeatureTestCase(EngineTestCase, OfflineTestCase):
    def setUp(self):
        super(OfflineFeatureTestCase, self).setUp()

        self.feature_m_patch = mock.patch('flowhub.engine.FeatureManager')
        self.feature_m_mock = self.feature_m_patch.start()
        self._produce_engine()

    def tearDown(self):
        self.feature_m_patch.stop()
        super(OfflineFeatureTestCase, self).tearDown()

    def test_start_all_defaults(self):
        self.assertFalse(self.engine._create_feature())

    def test_start(self):
        name = id_generator()
        self.assertTrue(self.engine._create_feature(name))

        self.feature_m_mock.assert_has_calls([
            mock.call().start(name, True, mock.ANY),
        ])

    def test_start_with_tracking(self):
        name = id_generator()

        self.assertTrue(self.engine._create_feature(name, False))

        self.feature_m_mock.assert_has_calls([
            mock.call().start(name, False, mock.ANY),
        ])

    def test_work_all_defaults(self):
        self.assertFalse(self.engine.work_feature())

    def test_work_single_branch(self):
        name = id_generator()
        branch = mock.MagicMock()
        self.feature_m_mock().fuzzy_get.return_value = [branch]

        self.engine.work_feature(name)

        self.feature_m_mock.assert_has_calls([
            mock.call().fuzzy_get(name),
        ])
        branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_work_multiple_branches(self):
        name = id_generator()
        branch = mock.MagicMock()
        self.feature_m_mock().fuzzy_get.return_value = [branch, branch]

        self.engine.work_feature(name)

        self.feature_m_mock.assert_has_calls([
            mock.call().fuzzy_get(name),
        ])
        self.assertEqual(branch.call_count, 0)

    def test_accept_all_defaults(self):
        self.assertFalse(self.engine._accept_feature())

    def test_accept(self):
        name = id_generator()
        return_branch = mock.MagicMock()
        self.git_mock().head.reference = return_branch

        self.assertTrue(self.engine._accept_feature(name))

        self.feature_m_mock.assert_has_calls([
            mock.call().accept(
                name,
                summary=mock.ANY,
                with_delete=True,
            ),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_accept_while_on_branch(self):
        name = id_generator()
        self.git_mock().head.reference.name = self.repository_structure['feature'] + name
        return_branch = self.engine.develop

        self.assertTrue(self.engine._accept_feature())

        self.feature_m_mock.assert_has_calls([
            mock.call().accept(name, summary=mock.ANY, with_delete=True),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_abandon_all_defaults(self):
        self.assertFalse(self.engine._abandon_feature())

    def test_abandon(self):
        name = id_generator()
        return_branch = mock.MagicMock()
        self.git_mock().head.reference = return_branch

        self.assertTrue(self.engine._abandon_feature(name))

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

        self.feature_m_mock.assert_has_calls([
            mock.call().abandon(name, summary=mock.ANY),
        ])

    def test_abandon_while_on_branch(self):
        name = id_generator()
        self.git_mock().head.reference.name = self.repository_structure['feature'] + name
        return_branch = self.engine.develop

        self.assertTrue(self.engine._abandon_feature())

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

        self.feature_m_mock.assert_has_calls([
            mock.call().abandon(name, summary=mock.ANY),
        ])

    def test_publish_all_defaults(self):
        self.assertFalse(self.engine._publish_feature())

    def test_publish(self):
        name = id_generator()

        self.assertTrue(self.engine._publish_feature(name))

        self.feature_m_mock.assert_has_calls([
            mock.call().publish(name, mock.ANY),
        ])


class OnlineFeatureTestCase(EngineTestCase, OnlineTestCase):
    def setUp(self):
        super(OnlineFeatureTestCase, self).setUp()

        self.feature_m_patch = mock.patch('flowhub.engine.FeatureManager')
        self.feature_m_mock = self.feature_m_patch.start()
        self._produce_engine()

    def test_publish(self):
        name = id_generator()
        b = mock.MagicMock()
        self.feature_m_mock().publish.return_value = b

        self.assertTrue(self.engine._publish_feature(name))

        self.feature_m_mock.assert_has_calls([
            mock.call().publish(name, mock.ANY),
        ])


