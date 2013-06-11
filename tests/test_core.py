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

import itertools
import os
import random
import string
from subprocess import CalledProcessError
import unittest

import mock

from flowhub.core import *
from flowhub.managers import TagInfo
from tests import id_generator


class CoreTestCase(unittest.TestCase):
    def setUp(self):
        self.engine_patch = mock.patch("flowhub.engine.Engine")

        self.args = mock.MagicMock()
        self.engine_mock = self.engine_patch.start()

    def tearDown(self):
        self.engine_patch.stop()


class HookTestCase(CoreTestCase):
    def setUp(self):
        super(HookTestCase, self).setUp()

        self.subprocess_patch = mock.patch('subprocess.check_call')
        self.subprocess_mock = self.subprocess_patch.start()

    def tearDown(self):
        self.subprocess_patch.stop()

        super(HookTestCase, self).tearDown()

    def test_no_verify(self):
        self.args.no_verify = True

        self.assertTrue(do_hook(self.args, self.engine_mock, id_generator()))
        self.assertEqual(self.subprocess_mock.call_count, 0)

    def test_successful_hook(self):
        self.args.no_verify = False
        hook_name = id_generator()
        self.engine_mock._repo.git_dir = id_generator()

        self.assertTrue(do_hook(self.args, self.engine_mock, hook_name))
        self.subprocess_mock.assert_has_calls([
            mock.call(
                ((os.path.join(self.engine_mock._repo.git_dir, 'hooks', hook_name)),),
            ),
        ])

    def test_no_such_hook(self):
        self.args.no_verify = False
        hook_name = id_generator()
        self.subprocess_mock.side_effect = OSError

        self.assertTrue(do_hook(self.args, self.engine_mock, hook_name))

    def test_with_failed_hook(self):
        self.args.no_verify = False
        hook_name = id_generator()
        self.subprocess_mock.side_effect = CalledProcessError(None, None, None)

        self.assertFalse(do_hook(self.args, self.engine_mock, hook_name))


class InitCallTestCase(CoreTestCase):

    def test_correct_setup_defaults(self):
        inputs = ["REPO_NAME", "", "", "", "", "", "", ""]
        input_gen = itertools.islice(inputs, None)

        def input_func(query_str):
            return input_gen.next()

        output_func = lambda x: None

        handle_init_call(self.args, self.engine_mock, input_func=input_func, output_func=output_func)

        self.engine_mock.assert_has_calls([
            mock.call.setup_repository_structure(
                "REPO_NAME",
                "origin",
                "canon",
                "master",
                "develop",
                "feature/",
                "release/",
                "hotfix/",
            ),
        ])

    def test_correct_setup(self):
        inputs = [id_generator() for x in range(8)]
        input_gen = itertools.islice(inputs, None)

        def input_func(query_str):
            return input_gen.next()

        output_func = lambda x: None

        handle_init_call(self.args, self.engine_mock, input_func, output_func)

        self.engine_mock.assert_has_calls([
            mock.call.setup_repository_structure(*inputs)
        ])


class FeatureCallTestCase(CoreTestCase):
    def test_start(self):
        self.args.action = "start"
        self.args.issue_num = None
        self.args.name = id_generator(chars=string.ascii_letters)
        self.args.track = False

        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True
            handle_feature_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(self.args, self.engine_mock, "post-feature-start")
            ])

            self.engine_mock.assert_has_calls([
                mock.call.create_feature(
                    name=self.args.name,
                    with_tracking=self.args.track,
                ),
            ])

    def test_start_with_issue_number(self):
        self.args.action = "start"
        self.args.name = id_generator(chars=string.ascii_letters)
        self.args.issue_num = id_generator(chars=string.digits)
        expected_name = "{}-{}".format(self.args.issue_number, self.args.name)
        self.args.track = False

        handle_feature_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.create_feature(
                name=expected_name,
                with_tracking=self.args.track,
            ),
        ])

    def test_work(self):
        self.args.action = "work"
        self.args.issue = None
        self.args.identifier = id_generator()
        handle_feature_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.work_feature(name=self.args.identifier),
        ])

    def test_work_with_issue_num(self):
        self.args.action = "work"
        self.args.issue = True
        self.args.identifier = id_generator()
        handle_feature_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.work_feature(issue=self.args.identifier),
        ])

    def test_publish(self):
        self.args.action = "publish"
        self.args.name = id_generator()
        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True

            handle_feature_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(self.args, self.engine_mock, "pre-feature-publish")
            ])

            self.engine_mock.assert_has_calls([
                mock.call.publish_feature(name=self.args.name),
            ])

    def test_publish_failed_hook(self):
        self.args.action = "publish"
        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = False
            handle_feature_call(self.args, self.engine_mock)

            self.assertEqual(self.engine_mock.call_count, 0)

    def test_abandon(self):
        self.args.action = "abandon"
        self.args.name = id_generator()
        handle_feature_call(self.args, self.engine_mock)
        self.engine_mock.assert_has_calls([
            mock.call.abandon_feature(name=self.args.name),
        ])

    def test_accepted(self):
        self.args.action = 'accepted'
        self.args.name = id_generator()
        self.args.no_delete = False

        handle_feature_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.accept_feature(
                name=self.args.name,
                delete_feature_branch=True,
            ),
        ])

    def test_accepted_no_delete(self):
        self.args.action = 'accepted'
        self.args.name = id_generator()
        self.args.no_delete = True

        handle_feature_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.accept_feature(
                name=self.args.name,
                delete_feature_branch=False,
            ),
        ])

    def test_list(self):
        self.args.action = "list"
        handle_feature_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.list_features(),
        ])

    def test_undefined_action(self):
        self.args.action = id_generator()
        with self.assertRaises(RuntimeError):
            handle_feature_call(self.args, self.engine_mock)


class ReleaseCallTestCase(CoreTestCase):
    def test_start(self):
        self.args.action = "start"
        self.args.name = id_generator()

        with mock.patch('flowhub.core.do_hook') as patch:
            handle_release_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(self.args, self.engine_mock, "post-release-start", self.args.name),
            ])

            self.engine_mock.assert_has_calls([
                mock.call.start_release(name=self.args.name),
            ])

    def test_publish_with_name(self):
        self.args.action = "publish"
        self.args.no_cleanup = False
        self.args.name = id_generator()

        with mock.patch('flowhub.core.do_hook') as patch:
            handle_release_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(self.args, self.engine_mock, "pre-release-publish"),
                mock.call().__nonzero__(),  # the if check
                mock.call(self.args, self.engine_mock, "post-release-publish", mock.ANY),
            ])

            self.engine_mock.assert_has_calls([
                mock.call.publish_release(
                    name=self.args.name,
                    with_delete=not self.args.no_cleanup,
                    tag_info=TagInfo(
                        self.engine_mock.release.name.replace().strip(),
                        "",
                    )
                ),
            ])

    def test_publish_failed_hook(self):
        self.args.action = "publish"
        self.args.name = id_generator()

        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = False

            handle_release_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(self.args, self.engine_mock, "pre-release-publish"),
            ])

            self.assertEqual(self.engine_mock.call_count, 0)

    def test_contribute(self):
        self.args.action = "contribute"

        handle_release_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.contribute_release(),
        ])


class HotfixCallTestCase(CoreTestCase):
    def test_start(self):
        self.args.action = "start"
        self.args.name = id_generator()
        self.args.issue_numbers = []

        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True

            handle_hotfix_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(
                    self.args,
                    self.engine_mock,
                    "post-hotfix-start",
                    self.args.name,
                ),
            ])

            self.engine_mock.assert_has_calls([
                mock.call.start_hotfix(
                    name=self.args.name,
                    issues=self.args.issue_numbers
                )
            ])

    def test_publish_with_name(self):
        self.args.action = "publish"
        self.args.name = id_generator()
        self.args.issue_numbers = []
        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True

            handle_hotfix_call(self.args, self.engine_mock)

            patch.assert_has_calls([
                mock.call(self.args, self.engine_mock, 'pre-hotfix-publish'),
                mock.call(self.args, self.engine_mock, 'post-hotfix-publish', mock.ANY),

            ])

            self.engine_mock.assert_has_calls([
                mock.call.publish_hotfix(
                    name=self.args.name,
                    tag_info=TagInfo(
                        self.engine_mock.hotfix.name.replace().strip(),
                        "",
                    )
                ),
            ])

    def test_contribute(self):
        self.args.action = "contribute"

        handle_hotfix_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.contribute_hotfix(),
        ])


class CleanupCallTestCase(CoreTestCase):
    OPTIONS = ['t', 'u', 'r']

    def test_option_combinations(self):

        for l in range(1, len(self.OPTIONS)+1):

            for combo in itertools.combinations(self.OPTIONS, l):
                # reset the chosen options
                for o in self.OPTIONS:
                    setattr(self.args, o, False)
                self.args.all = False

                print combo
                for choice in combo:
                    setattr(self.args, choice, True)

                handle_cleanup_call(self.args, self.engine_mock)

                self.engine_mock.assert_has_calls([
                    mock.call.cleanup_branches(targets=''.join(combo))
                ])
                self.engine_patch.stop()
                self.engine_patch.start()

    def test_all(self):
        for o in self.OPTIONS:
            setattr(self.args, o, False)
        self.args.all = True

        handle_cleanup_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.cleanup_branches(targets='tur')
        ])

    def test_no_targets(self):
        for o in self.OPTIONS:
            setattr(self.args, o, False)
        self.args.all = False

        handle_cleanup_call(self.args, self.engine_mock)

        self.assertEqual(self.engine_mock.call_count, 0)


class IssueCallTestCase(CoreTestCase):
    def test_start(self):
        self.args.action = "start"
        self.args.labels = False
        self.args.create_branch = bool(random.choice([0, 1]))

        handle_issue_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.open_issue(
                title=self.args.title,
                labels=None,
                create_branch=self.args.create_branch,
            )
        ])

    def test_start_with_labels(self):
        self.args.action = "start"
        self.args.labels = ",".join((id_generator() for x in range(5)))
        self.args.create_branch = bool(random.choice([0, 1]))

        handle_issue_call(self.args, self.engine_mock)

        self.engine_mock.assert_has_calls([
            mock.call.open_issue(
                title=self.args.title,
                labels=self.args.labels.split(','),
                create_branch=self.args.create_branch,
            )
        ])
