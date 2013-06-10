from subprocess import CalledProcessError
import unittest


from flowhub.core import *


class InitCallTestCase(unittest.TestCase):
    def setUp(self):
        self.assertFalse(True)


class FeatureCallTestCase(unittest.TestCase):
    def setUp(self):
        self.assertFalse(True)


class ReleaseCallTestCase(unittest.TestCase):
    def setUp(self):
        self.assertFalse(True)


class HotfixCallTestCase(unittest.TestCase):
    def setUp(self):
        self.assertFalse(True)


class CleanupCallTestCase(unittest.TestCase):
    def setUp(self):
        self.assertFalse(True)


class IssueCallTestCase(unittest.TestCase):
    def setUp(self):
        self.assertFalse(True)

# class OnlineHooksTestCase(unittest.TestCase):
#     def setUp(self):
#         super(OnlineTestCase, self).setUp()
#         self.engine = Engine(offline=True, debug=0)
#         self._do_setup_things()
#         self.repo.create_remote(self.setup_args["origin"], id_generator())
#         self.repo.create_remote(self.setup_args["canon"], id_generator())

#         # checkout the "master" branch
#         getattr(self.repo.branches, self.setup_args['master']).checkout()

#         self.engine = Engine(offline=False, debug=0)

#     def test_hook_DNE(self):
#         self._setup_engine()

#         with mock.patch('subprocess.check_call') as patch:
#             patch.side_effect = OSError
#             self.engine._create_feature(self.BRANCH_NAME)

#         self.assertHasBranch(self.setup_args['feature'] + self.BRANCH_NAME)

#     def test_hook_error(self):
#         self._setup_engine()

#         with mock.patch('subprocess.check_call') as patch:
#             patch.side_effect = CalledProcessError(None, None, None)
#             self.assertFalse(self.engine._create_feature(self.BRANCH_NAME))

#     def _setup_engine(self):
#         self.engine._repo.git = mock.Mock()
#         self.engine._create_pull_request = mock.Mock()
#         self.BRANCH_NAME = id_generator()

#     def test_pre_feature_publish_hook(self):
#         self._setup_engine()

#         self.engine._do_hook = mock.Mock()
#         self.engine._create_feature(self.BRANCH_NAME)
#         self.engine._publish_feature(self.BRANCH_NAME)

#         self.engine._do_hook.assert_has_calls([
#             mock.call("pre-feature-publish"),
#         ])

#     def test_post_feature_start_hook(self):
#         self._setup_engine()
#         self.engine._do_hook = mock.Mock()
#         self.engine._create_feature(self.BRANCH_NAME)

#         self.engine._do_hook.assert_has_calls([
#             mock.call("post-feature-start"),
#         ])

#     def test_post_release_start_hook(self):
#         self._setup_engine()
#         self.engine._do_hook = mock.Mock()
#         with mock.patch("git.remote.Remote.push"):
#             self.engine._start_release(self.BRANCH_NAME)

#         self.engine._do_hook.assert_has_calls([
#             mock.call("post-release-start"),
#         ])

#     def test_pre_release_publish_hook(self):
#         self._setup_engine()
#         self.engine._do_hook = mock.Mock()
#         with mock.patch("git.remote.Remote.push"):
#             self.engine._start_release(self.BRANCH_NAME)
#             with mock.patch("git.remote.Remote.fetch"):
#                 self.engine._publish_release(
#                     self.BRANCH_NAME,
#                     delete_release_branch=False,
#                     tag_label="NOTHING",
#                     tag_message="NOTHING",
#                 )

#         self.engine._do_hook.assert_has_calls([
#             mock.call("pre-release-publish"),
#         ])

#     def test_post_hotfix_start_hook(self):
#         self._setup_engine()
#         self.engine._do_hook = mock.Mock()
#         with mock.patch("git.remote.Remote.push"):
#             with mock.patch("git.remote.Remote.fetch"):
#                 self.engine._start_hotfix(self.BRANCH_NAME)

#         self.engine._do_hook.assert_has_calls([
#             mock.call("post-hotfix-start"),
#         ])

#     def test_pre_hotfix_publish_hook(self):
#         self._setup_engine()
#         self.engine._do_hook = mock.Mock()
#         with mock.patch("git.remote.Remote.push"):
#             with mock.patch("git.remote.Remote.fetch"):
#                 self.engine._start_hotfix(self.BRANCH_NAME)
#                 self.engine._publish_hotfix(
#                     self.BRANCH_NAME,
#                     delete_hotfix_branch=False,
#                     tag_label="NOTHING",
#                     tag_message="NOTHING",
#                 )

#         self.engine._do_hook.assert_has_calls([
#             mock.call("pre-hotfix-publish"),
#         ])
