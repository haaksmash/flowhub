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
import unittest

from tests import (
    id_generator,
)

from flowhub.engine import Engine
from flowhub.managers import TagInfo


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

        self.feature_m_patch = mock.patch('flowhub.engine.FeatureManager')
        self.feature_m_mock = self.feature_m_patch.start()
        self.release_m_patch = mock.patch('flowhub.engine.ReleaseManager')
        self.release_m_mock = self.release_m_patch.start()
        self.hotfix_m_patch = mock.patch('flowhub.engine.HotfixManager')
        self.hotfix_m_mock = self.hotfix_m_patch.start()
        self.pull_m_patch = mock.patch('flowhub.engine.PullRequestManager')
        self.pull_m_mock = self.pull_m_patch.start()

    def tearDown(self):
        super(EngineTestCase, self).tearDown()
        self.pull_m_patch.stop()
        self.hotfix_m_patch.stop()
        self.release_m_patch.stop()
        self.feature_m_patch.stop()
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
        for key in ["name", "origin", "canon", "master", "develop"]:
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
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        self.release_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['release'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        self.hotfix_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['hotfix'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        self.pull_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['name'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
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
        for key in ["name", "origin", "canon", "master", "develop"]:
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
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=self.gh_mock(),
                offline=False
            ),
        ])

        self.release_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['release'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=self.gh_mock(),
                offline=False
            ),
        ])

        self.hotfix_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['hotfix'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=self.gh_mock(),
                offline=False
            ),
        ])

        self.pull_m_mock.assert_has_calls([
            mock.call(
                debug=self.engine.DEBUG,
                prefix=self.repository_structure['name'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=self.gh_mock(),
                offline=False
            ),
        ])


class OfflineFeatureTestCase(EngineTestCase, OfflineTestCase):
    def setUp(self):
        super(OfflineFeatureTestCase, self).setUp()
        self._produce_engine()

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

        self.assertFalse(self.engine._publish_feature(name))


class OnlineFeatureTestCase(EngineTestCase, OnlineTestCase):
    def setUp(self):
        super(OnlineFeatureTestCase, self).setUp()
        self._produce_engine()

    def test_publish(self):
        name = id_generator()
        b = mock.MagicMock()
        self.feature_m_mock().publish.return_value = b

        self.assertTrue(self.engine._publish_feature(name))

        self.feature_m_mock.assert_has_calls([
            mock.call().publish(name, mock.ANY),
        ])


class OfflineReleaseTestCase(EngineTestCase, OfflineTestCase):
    def setUp(self):
        super(OfflineReleaseTestCase, self).setUp()
        self._produce_engine()

    def test_start_all_defaults(self):
        self.assertFalse(self.engine._start_release())

    def test_start(self):
        name = id_generator()
        new_branch = mock.MagicMock()
        self.release_m_mock().start.return_value = new_branch
        self.assertTrue(self.engine._start_release(name))

        self.release_m_mock.assert_has_calls([
            mock.call().start(name, mock.ANY),
        ])

        new_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_start_with_existing_release(self):
        name = id_generator()

        release_mock = mock.MagicMock()
        release_mock.name.startswith.return_value = True
        self.git_mock().branches = [release_mock]

        self.assertFalse(self.engine._start_release(name))

        self.assertEqual(self.release_m_mock().call_count, 0)

    def test_publish_all_defaults(self):
        self.assertFalse(self.engine._publish_release())

    def test_publish_with_name(self):
        name = id_generator()

        self.assertTrue(self.engine._publish_release(name))

        self.release_m_mock.assert_has_calls([
            mock.call().publish(name, True, None, mock.ANY)
        ])

    def test_publish_on_release_branch(self):
        return_branch = self.engine.develop
        self.git_mock().head.reference.name = self.repository_structure['release'] + id_generator()

        self.assertTrue(self.engine._publish_release())

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_publish_with_name_tag_info_and_no_delete(self):
        name = id_generator()
        tag_label = id_generator()
        tag_message = id_generator()

        self.assertTrue(
            self.engine._publish_release(
                name,
                with_delete=False,
                tag_info=TagInfo(tag_label, tag_message),
            ),
        )

        self.release_m_mock.assert_has_calls([
            mock.call().publish(name, False, TagInfo(tag_label, tag_message), mock.ANY)
        ])

    def test_contribute(self):
        self.assertFalse(self.engine.contribute_release())


class OnlineReleaseTestCase(EngineTestCase, OnlineTestCase):
    def setUp(self):
        super(OnlineReleaseTestCase, self).setUp()
        self._produce_engine()

    def test_contribute(self):
        release_mock = mock.MagicMock()
        release_mock.name.startswith.return_value = True
        release_mock.commit = True

        self.git_mock().branches = [release_mock]

        self.git_mock().head.reference.object.iter_parents.return_value = [True]

        self.assertTrue(self.engine._contribute_release())

        self.release_m_mock.assert_has_calls([
            mock.call().contribute(self.git_mock().head.reference, mock.ANY),
        ])


class OfflineHotfixTestCase(EngineTestCase, OfflineTestCase):
    def setUp(self):
        super(OfflineHotfixTestCase, self).setUp()
        self._produce_engine()

    def test_start_all_defaults(self):
        self.assertFalse(self.engine._start_hotfix())

    def test_start(self):
        name = id_generator()
        return_branch = self.hotfix_m_mock().start()

        self.assertTrue(self.engine._start_hotfix(name))

        self.hotfix_m_mock.assert_has_calls([
            mock.call().start(name, None, mock.ANY),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_start_with_issues(self):
        name = id_generator()
        issues = mock.MagicMock()
        return_branch = self.hotfix_m_mock().start()

        self.assertTrue(self.engine._start_hotfix(name, issues))

        self.hotfix_m_mock.assert_has_calls([
            mock.call().start(name, issues, mock.ANY),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_start_with_existing_hotfix(self):
        name = id_generator()

        hotfix_mock = mock.MagicMock()
        hotfix_mock.name.startswith.return_value = True
        self.git_mock().branches = [hotfix_mock]

        self.assertFalse(self.engine._start_hotfix(name))

        self.assertEqual(self.hotfix_m_mock().call_count, 0)

    def test_publish_all_defaults(self):
        self.assertFalse(self.engine._publish_hotfix())

    def test_publish_not_on_hotfix_branch(self):
        name = id_generator()

        return_branch = mock.MagicMock()
        self.git_mock().head.reference = return_branch

        self.assertTrue(self.engine._publish_hotfix(name))

        self.hotfix_m_mock.assert_has_calls([
            mock.call().publish(name, None, True, mock.ANY),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_publish_on_hotfix_branch(self):
        return_branch = self.engine.develop
        self.git_mock().head.reference.name = self.repository_structure['hotfix'] + id_generator()

        self.assertTrue(self.engine._publish_hotfix())

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_contribute(self):
        self.assertFalse(self.engine._contribute_hotfix())


class OnlineHotfixTestCase(EngineTestCase, OnlineTestCase):
    def setUp(self):
        super(OnlineHotfixTestCase, self).setUp()
        self._produce_engine()

    def test_contribute(self):
        hotfix_mock = mock.MagicMock()
        hotfix_mock.name.startswith.return_value = True
        hotfix_mock.commit = True

        self.git_mock().branches = [hotfix_mock]

        self.git_mock().head.reference.object.iter_parents.return_value = [True]

        self.assertTrue(self.engine._contribute_hotfix())

        self.release_m_mock.assert_has_calls([
            mock.call().contribute(self.git_mock().head.reference, mock.ANY),
        ])

    def test_contribute_on_wrong_branch_by_existance(self):
        self.git_mock().branches = []
        self.assertFalse(self.engine._contribute_hotfix())

    def test_contribute_on_wrong_branch_by_commit(self):
        hotfix_mock = mock.MagicMock()
        hotfix_mock.name.startswith.return_value = True

        self.git_mock().branches = [hotfix_mock]

        # ensure that the "commit" isn't in the iter_parents
        hotfix_mock.commit = False
        self.git_mock().head.reference.object.iter_parents.return_value = [True]

        self.assertFalse(self.engine._contribute_hotfix())

