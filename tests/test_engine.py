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
import subprocess
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
            raise subprocess.CalledProcessError(None, None)

        with mock.patch("subprocess.check_output") as patch:
            patch.side_effect = raise_call_error

            with self.assertRaises(git.exc.InvalidGitRepositoryError):
                Engine(skip_auth=True)


class OfflineTestCase(unittest.TestCase):
    def setUp(self):
        # create new repository
        print "Creating new test repo..."
        self.mock_gh_p = mock.patch('flowhub.engine.Github')
        self.mock_gh = self.mock_gh_p.start()
        self.repo = git.Repo.init(TEST_REPO)
        # make an initial commit
        self.repo.index.commit("Initial commit")
        self.mock_gh.start()

        os.chdir(TEST_REPO)
        self.engine = Engine(skip_auth=True, debug=0)

    def tearDown(self):
        # ensure no web-talking functions were called:
        self.assertFalse(self.mock_gh.called)
        self.mock_gh_p.stop()

        shutil.rmtree(TEST_REPO)
        print "tearing down test repo"

    def _do_setup_things(self, engine=None, **kwargs):
        if engine is None:
            engine = self.engine

        self.setup_args = {
            "origin": kwargs.get("origin", id_generator()),
            "canon": kwargs.get("canon", id_generator()),
            "master": kwargs.get("master", id_generator()),
            "develop": kwargs.get("develop", id_generator()),
            "feature": kwargs.get("feature", id_generator()),
            "release": kwargs.get("release", id_generator()),
            "hotfix": kwargs.get("hotfix", id_generator()),
        }

        self.engine.setup_repository_structure(
            name=REPO_NAME,
            **self.setup_args
        )


class OnlineTestCase(OfflineTestCase):
    def setUp(self):
        print "Creating new test repo..."
        self.mock_gh_p = mock.patch('flowhub.engine.Github', autospec=True)
        self.mock_gh = self.mock_gh_p.start()
        self.repo = git.Repo.init(TEST_REPO)
        # make an initial commit
        self.repo.index.commit("Initial commit")

        os.chdir(TEST_REPO)

    def tearDown(self):
        self.mock_gh_p.stop()
        shutil.rmtree(TEST_REPO)
        print "tearing down test repo"


class OfflineSetupTestCase(OfflineTestCase):

    def test_setup_repo_structure(self):
        args = {
            "origin": id_generator(),
            "canon": id_generator(),
            "master": id_generator(),
            "develop": id_generator(),
            "feature": id_generator(),
            "release": id_generator(),
            "hotfix": id_generator(),
        }
        self._do_setup_things(**args)

        # we care about the config reader.
        self.assertEqual(self.engine._cr.flowhub.structure.master, args["master"])
        self.assertEqual(self.engine._cr.flowhub.structure.develop, args["develop"])

        # these branches should have been created
        self.engine.master
        self.engine.develop

        self.assertEqual(self.engine._cr.flowhub.structure.origin, args["origin"])
        self.assertEqual(self.engine._cr.flowhub.structure.canon, args["canon"])

        self.assertEqual(self.engine._cr.flowhub.prefix.feature, args["feature"])
        self.assertEqual(self.engine._cr.flowhub.prefix.release, args["release"])
        self.assertEqual(self.engine._cr.flowhub.prefix.hotfix, args["hotfix"])

    def test_get_repo(self):
        self.engine = Engine(skip_auth=True)
        self._do_setup_things()

        self.assertEqual(self.repo, self.engine._get_repo())


class OnlineSetupTestCase(OnlineTestCase):
    def teardown(self):
        super(OnlineTestCase, self).tearDown()
        self.engine = None

    def test_setup_repo_structure(self):
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things()
        self.engine = Engine(skip_auth=False, debug=0)

    def test_setup_no_token(self):

        def make_mock_gh():
            self.engine._gh = mock.MagicMock()

        self.mock_gh.side_effect = AttributeError
        # because interaction is hard to mock, just...mock it all the way out.
        with mock.patch('flowhub.engine.Engine._create_token') as patch:
            patch.return_value = True
            patch.side_effect = make_mock_gh
            self.engine = Engine(skip_auth=True, debug=0)
            self._do_setup_things()
            self.engine = Engine(skip_auth=False, debug=0)

            self.assertTrue(patch.called)

        del self.mock_gh.side_effect


class OfflineBranchFindingTestCase(OfflineTestCase):
    def setUp(self):
        # create new repository
        print "Creating new test repo..."
        self.mock_gh_p = mock.patch('github.Github')
        self.mock_gh = self.mock_gh_p.start()
        self.repo = git.Repo.init(TEST_REPO)
        # make an initial commit
        self.repo.index.commit("Initial commit")
        self.repo_structure = {
            "origin": id_generator(),
            "canon": id_generator(),
            "master": id_generator(),
            "develop": id_generator(),
            "feature": id_generator(),
            "release": id_generator(),
            "hotfix": id_generator(),
        }

        self.repo.create_remote(self.repo_structure['origin'], "None")
        self.repo.create_remote(self.repo_structure['canon'], "None")

        os.chdir(TEST_REPO)
        self.engine = Engine(skip_auth=True, debug=1)
        self._do_setup_things(**self.repo_structure)

    def test_develop_is_develop(self):
        self.assertEqual(
            self.engine.develop,
            getattr(self.repo.heads, self.repo_structure['develop'])
        )

    def test_get_develop_no_develop(self):
        self.engine._cr.flowhub.structure.develop = id_generator()
        with self.assertRaises(NoSuchBranch):
            self.engine.develop

    def test_master_is_master(self):
        self.assertEqual(
            self.engine.master,
            getattr(self.repo.heads, self.repo_structure['master'])
        )

    def test_get_master_no_master(self):
        self.engine._cr.flowhub.structure.master = id_generator()
        with self.assertRaises(NoSuchBranch):
            self.engine.master

    def test_branch_exists(self):
        self.assertTrue(self.engine._branch_exists(self.repo_structure['master']))
        self.assertFalse(self.engine._branch_exists(id_generator()))

    def test_can_find_release(self):
        release = self.repo.create_head(
            '/'.join([self.repo_structure['release'], "test_release"])
        )
        self.assertEqual(self.engine.release, release)

    def test_can_find_hotfix(self):
        hotfix = self.repo.create_head('/'.join(
            [self.repo_structure['hotfix'], "test_hotfix"])
        )
        self.assertEqual(self.engine.hotfix, hotfix)


class RepositoryBaseTestCase(unittest.TestCase):

    def assertHasBranch(self, branchname):
        self.assertTrue(hasattr(self.repo.heads, branchname))

    def assertNotHasBranch(self, branchname):
        self.assertFalse(hasattr(self.repo.heads, branchname))

    def assertOnBranch(self, branchname):
        self.assertEqual(self.repo.head.reference, getattr(self.repo.heads, branchname))

    def assertNotOnBranch(self, branchname):
        self.assertNotEqual(self.repo.head.reference, getattr(self.repo.heads, branchname))


class OfflineFeatureTestCase(OfflineTestCase, RepositoryBaseTestCase):
    def setUp(self):
        super(OfflineFeatureTestCase, self).setUp()

        self.repo.index.commit("Initial commit")
        self.repo_structure = {
            "origin": id_generator(),
            "canon": id_generator(),
            "master": id_generator(),
            "develop": id_generator(),
            "feature": id_generator(),
            "release": id_generator(),
            "hotfix": id_generator(),
        }

        self._do_setup_things(**self.repo_structure)

    def test_create_feature_no_name(self):
        brances_before = list(self.repo.heads)

        self.assertFalse(self.engine._create_feature())

        self.assertEqual(list(self.repo.heads), brances_before)

    def test_create_feature(self):
        FEATURE_NAME = id_generator()
        expected_branch_name = "{}{}".format(self.repo_structure['feature'], FEATURE_NAME)

        self.assertTrue(self.engine._create_feature(FEATURE_NAME))

        # should have created and checked out the new feature branch.
        self.assertHasBranch(expected_branch_name)
        self.assertOnBranch(expected_branch_name)

    def test_work_feature_by_name(self):
        FEATURE_NAME = id_generator()
        self.engine._create_feature(FEATURE_NAME)
        getattr(self.repo.branches, self.repo_structure['develop']).checkout()

        self.engine.work_feature(name=FEATURE_NAME)

        self.assertOnBranch(self.repo_structure['feature'] + FEATURE_NAME)

    def test_work_feature_by_issue(self):
        ISSUE_NUM = id_generator(chars=string.digits)
        FEATURE_NAME = ISSUE_NUM + "-" + id_generator()
        self.engine._create_feature(FEATURE_NAME)
        getattr(self.repo.branches, self.repo_structure['develop']).checkout()

        self.engine.work_feature(issue=ISSUE_NUM)

        self.assertOnBranch(self.repo_structure['feature'] + FEATURE_NAME)

    def test_abandon_feature(self):
        ISSUE_NUM = id_generator(chars=string.digits)
        FEATURE_NAME = ISSUE_NUM + "-" + id_generator()
        self.engine._create_feature(FEATURE_NAME)

        self.engine._abandon_feature()
        self.assertNotHasBranch(FEATURE_NAME)
        self.assertOnBranch(self.engine.develop.name)

    def test_abandon_feature_by_name(self):
        ISSUE_NUM = id_generator(chars=string.digits)
        FEATURE_NAME = ISSUE_NUM + "-" + id_generator()
        self.engine._create_feature(FEATURE_NAME)
        FEATURE_2_NAME = id_generator()
        # create a new feature to switch to it
        self.engine._create_feature(FEATURE_2_NAME)
        self.engine._abandon_feature(FEATURE_NAME)

        self.assertHasBranch(self.setup_args['feature']+FEATURE_2_NAME)
        self.assertNotHasBranch(FEATURE_NAME)
        self.assertOnBranch(self.setup_args['feature']+FEATURE_2_NAME)

    def test_list_features(self):
        features = []
        for i in range(5):
            FEATURE_NAME = id_generator()
            self.engine._create_feature(FEATURE_NAME)
            features.append(self.repo_structure['feature'] + FEATURE_NAME)

        for i in range(5):
            self.repo.create_head(
                id_generator(),
                commit=self.engine.develop,
            )

        listed_features = self.engine.list_features()

        for feature in listed_features:
            self.assertIn(feature.name, features)


class OnlineFeatureTestCase(OnlineTestCase, RepositoryBaseTestCase):
    def setUp(self):
        super(OnlineTestCase, self).setUp()
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things()
        self.repo.create_remote(self.setup_args["origin"], id_generator())
        self.repo.create_remote(self.setup_args["canon"], id_generator())
        self.engine = Engine(skip_auth=False, debug=0)

    def test_create_with_tracking_branch(self):
        FEATURE_NAME = id_generator()
        patch = mock.Mock()
        self.engine._repo.git = patch

        self.engine._create_feature(FEATURE_NAME, True)
        patch.assert_has_calls([
            mock.call.push(
                self.setup_args['origin'],
                self.setup_args['feature']+FEATURE_NAME,
                set_upstream=True,
            )
        ])

    def test_abandon(self):
        self.engine._repo.git = mock.Mock()
        FEATURE_NAME = id_generator()

        # create a feature to abandon...
        self.engine._create_feature(FEATURE_NAME, create_tracking_branch=False)
        # and abandon it.
        self.engine._abandon_feature(FEATURE_NAME)

        # ensure that the abandon is pushed to origin.
        self.engine._repo.git.assert_has_calls([
            mock.call.push(
                self.setup_args['origin'],
                self.setup_args['feature']+FEATURE_NAME,
                delete=True,
                force=True,
            ),
        ])

    def _setup_publish_test(self):
        self.engine._repo.git = mock.Mock()
        self.engine._create_pull_request = mock.Mock()
        self.FEATURE_NAME = id_generator()

        self.engine._create_feature(self.FEATURE_NAME)

    def test_publish_origin_not_canon_new_pr(self):
        self._setup_publish_test()
        self.engine._publish_feature(self.FEATURE_NAME)

        self.engine._repo.git.push.assert_has_calls([
            mock.call.push(
                self.setup_args['origin'],
                self.setup_args['feature']+self.FEATURE_NAME,
                set_upstream=True,
            )
        ])

        self.assertEqual(self.engine._create_pull_request.call_count, 1)

    def test_publish_origin_is_canon(self):
        pass


class RemoteFindingTestCase(OfflineTestCase):
    def setUp(self):
        # create new repository
        print "Creating new test repo..."
        self.mock_gh_p = mock.patch('github.Github')
        self.mock_gh = self.mock_gh_p.start()
        self.repo = git.Repo.init(TEST_REPO)
        # make an initial commit
        self.repo.index.commit("Initial commit")
        self.mock_gh.start()

        os.chdir(TEST_REPO)

    def test_origin_is_origin(self):
        origin_name = id_generator()
        self.repo.create_remote(origin_name, id_generator())
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things(origin=origin_name)

        self.assertEqual(self.engine.origin, getattr(self.repo.remotes, origin_name))

    def test_get_origin_no_origin(self):
        origin_name = id_generator()
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things(origin=origin_name)

        with self.assertRaises(NoSuchRemote):
            self.engine.origin

    def test_canon_is_canon(self):
        canon_name = id_generator()
        self.repo.create_remote(canon_name, id_generator())
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things(canon=canon_name)
        self.assertEqual(self.engine.canon, getattr(self.repo.remotes, canon_name))

    def test_get_canon_no_canon(self):
        canon_name = id_generator()
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things(canon=canon_name)

        with self.assertRaises(NoSuchRemote):
            self.engine.canon

    def test_remote_exists(self):
        canon_name = id_generator()
        self.repo.create_remote(canon_name, id_generator())
        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things(canon=canon_name)
        self.assertTrue(self.engine._remote_exists(canon_name))
        self.assertFalse(self.engine._remote_exists(id_generator()))


class TestPullRequestCase(OnlineTestCase):
    def setUp(self):
        super(TestPullRequestCase, self).setUp()

        self.engine = Engine(skip_auth=True, debug=0)
        self._do_setup_things()
        self.repo.create_remote(self.setup_args["origin"], id_generator())
        self.repo.create_remote(self.setup_args["canon"], id_generator())
        self.engine = Engine(skip_auth=False, debug=0)

        self.base = id_generator()
        self.head = id_generator()

    def test_issue_match(self):
        issue_num = id_generator(chars=string.digits)
        self.head = issue_num + '-' + self.head

        self.engine._create_pull_request(self.base, self.head)
        self.engine.gh_canon.assert_has_calls([
            mock.call.get_issue(int(issue_num)),
            mock.call.create_pull(
                issue=mock.ANY,
                base=self.base,
                head=self.head,
            )
        ])

    def test_is_issue(self):
        with mock.patch('__builtin__.raw_input') as patch:
            issue_num = int(id_generator(chars=string.digits))
            c = itertools.cycle(['y', issue_num])
            patch.side_effect = lambda x: c.next()
            self.engine._open_issue = mock.Mock()
            self.engine._create_pull_request(self.base, self.head)

            self.engine.gh_canon.assert_has_calls([
                mock.call.get_issue(issue_num),
                mock.call.create_pull(
                    issue=mock.ANY,
                    base=self.base,
                    head=self.head,
                )
            ])

    def test_is_not_issue(self):
        with mock.patch('__builtin__.raw_input') as patch:
            patch.return_value = "N"
            self.engine._open_issue = mock.Mock()
            self.engine._create_pull_request(self.base, self.head)

            self.assertEqual(self.engine._open_issue.call_count, 1)

            self.engine.gh_canon.assert_has_calls([
                mock.call.create_pull(
                    issue=mock.ANY,
                    base=self.base,
                    head=self.head,
                )
            ])
