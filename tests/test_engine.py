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
from github import Github, GithubException
import mock
import os
import shutil
import subprocess
import unittest

from tests import (
    id_generator,
    USERNAME,
    PASSWORD,
    TEST_DIR,
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
        self.repo = git.Repo.init(TEST_REPO)
        # make an initial commit
        self.repo.index.commit("Initial commit")

        os.chdir(TEST_REPO)
        self.engine = Engine(skip_auth=True, debug=3)

    def tearDown(self):
        shutil.rmtree(TEST_REPO)
        print "tearing down test repo"

    def _do_setup_things(self, **kwargs):
        self.engine.setup_repository_structure(
            name=REPO_NAME,
            origin=kwargs.get("origin", id_generator()),
            canon=kwargs.get("canon", id_generator()),
            master=kwargs.get("master", id_generator()),
            develop=kwargs.get("develop", id_generator()),
            feature=kwargs.get("feature", id_generator()),
            release=kwargs.get("release", id_generator()),
            hotfix=kwargs.get("hotfix", id_generator()),
        )


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
        self.assertEqual(self.engine._cr.flowhub.structure.origin, args["origin"])
        self.assertEqual(self.engine._cr.flowhub.structure.canon, args["canon"])
        self.assertEqual(self.engine._cr.flowhub.prefix.feature, args["feature"])
        self.assertEqual(self.engine._cr.flowhub.prefix.release, args["release"])
        self.assertEqual(self.engine._cr.flowhub.prefix.hotfix, args["hotfix"])


class OfflineBranchFindingTestCase(OfflineTestCase):
    def setUp(self):
        # create new repository
        print "Creating new test repo..."
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

        # Ensure repo actually has the things we claim it has
        self.repo.create_head(self.repo_structure['master'])
        self.repo.create_head(self.repo_structure['develop'])
        self.repo.create_remote(self.repo_structure['origin'], "None")
        self.repo.create_remote(self.repo_structure['canon'], "None")

        os.chdir(TEST_REPO)
        self.engine = Engine(skip_auth=True, debug=4)
        self._do_setup_things(**self.repo_structure)

    def tearDown(self):
        shutil.rmtree(TEST_REPO)

    def test_develop_is_develop(self):
        self.assertEqual(self.engine.develop, getattr(self.repo.heads, self.repo_structure['develop']))

    def test_get_develop_no_develop(self):
        self.engine._cr.flowhub.structure.develop = id_generator()
        with self.assertRaises(NoSuchBranch):
            self.engine.develop

    def test_master_is_master(self):
        self.assertEqual(self.engine.master, getattr(self.repo.heads, self.repo_structure['master']))

    def test_get_master_no_master(self):
        self.engine._cr.flowhub.structure.master = id_generator()
        with self.assertRaises(NoSuchBranch):
            self.engine.master

    def test_origin_is_origin(self):
        print self.repo.remotes
        print self.repo_structure
        self.assertEqual(self.engine.origin, getattr(self.repo.remotes, self.repo_structure['origin']))

    def test_get_origin_no_origin(self):
        self.engine._cr.flowhub.structure.origin = id_generator()
        with self.assertRaises(NoSuchRemote):
            self.engine.origin

    def test_canon_is_canon(self):
        self.assertEqual(self.engine.canon, getattr(self.repo.remotes, self.repo_structure['canon']))

    def test_get_canon_no_canon(self):
        self.engine._cr.flowhub.structure.canon = id_generator()
        with self.assertRaises(NoSuchRemote):
            self.engine.canon

    def test_branch_exists(self):
        self.assertTrue(self.engine._branch_exists(self.repo_structure['master']))
        self.assertFalse(self.engine._branch_exists(id_generator()))

    def test_remote_exists(self):
        self.assertTrue(self.engine._remote_exists(self.repo_structure['canon']))
        self.assertFalse(self.engine._remote_exists(id_generator()))

    def test_can_find_release(self):
        release = self.repo.create_head('/'.join([self.repo_structure['release'], "test_release"]))
        self.assertEqual(self.engine.release, release)

    def test_can_find_hotfix(self):
        hotfix = self.repo.create_head('/'.join([self.repo_structure['hotfix'], "0.0.0"]))
        self.assertEqual(self.engine.hotfix, hotfix)


class OfflineFeatureTestCase(unittest.TestCase): pass
