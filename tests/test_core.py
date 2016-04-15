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
import pytest
import os
import string
from subprocess import CalledProcessError

import mock

from flowhub.core import (
    do_hook, handle_init_call, handle_issue_call, handle_hotfix_call,
    handle_cleanup_call, handle_feature_call, handle_release_call, create_tag_info
)
from flowhub.managers import TagInfo


@pytest.yield_fixture
def engine():
    with mock.patch("flowhub.engine.Engine") as engine_mock:
        yield engine_mock


@pytest.fixture
def args():
    return mock.MagicMock()


@pytest.yield_fixture
def subprocess_check_call():
    with mock.patch('subprocess.check_call') as subprocess_mock:
        yield subprocess_mock


@pytest.yield_fixture
def create_tag_info_mock():
    with mock.patch('flowhub.core.create_tag_info') as tag_info:
        yield tag_info


class CreateTagInfoTestCase(object):

    @pytest.yield_fixture(autouse=True)
    def mock_stdlib(self):
        with mock.patch('subprocess.check_call') as self.check_call, \
            mock.patch('tempfile.NamedTemporaryFile') as self.tempfile, \
            mock.patch('__builtin__.open') as self.open:
            yield

    def test_default_behaviors(self, args, subprocess_check_call):
        # "default" includes the editor being available and working
        subprocess_check_call.return_value = 0
        self.open.return_value.readlines.return_value = [
            'a bunch of',
            'individual',
            'lines',
        ]
        tag_info = create_tag_info(args, lambda s: "the_tag")

        assert tag_info == TagInfo("the_tag", "a bunch of individual lines")
        subprocess_check_call.assert_called_once_with(
            "$EDITOR {}".format(self.tempfile.return_value.name),
            shell=True,
        )
        self.open.assert_called_once_with(self.tempfile.return_value.name, 'r')
        self.open.return_value.close.assert_called_once_with()
        self.tempfile.return_value.close.assert_called_once_with()

    def test_handles_editor_failure(self, args, subprocess_check_call):
        subprocess_check_call.side_effect = OSError

        inputs = ["", "the body is here"]
        input_gen = itertools.islice(inputs, None)

        tag_info = create_tag_info(args, lambda s: input_gen.next())

        assert tag_info == TagInfo("", "the body is here")
        assert self.open.call_count == 0


class HookTestCase(object):
    def test_no_verify(self, engine, args, id_generator, subprocess_check_call):
        args.no_verify = True

        assert do_hook(args, engine, id_generator())
        assert subprocess_check_call.call_count == 0

    def test_successful_hook(self, args, engine, subprocess_check_call, id_generator):
        args.no_verify = False
        hook_name = id_generator()
        engine._repo.git_dir = id_generator()

        assert do_hook(args, engine, hook_name)
        subprocess_check_call.assert_has_calls([
            mock.call(
                ((os.path.join(engine._repo.git_dir, 'hooks', hook_name)),),
            ),
        ])

    def test_no_such_hook(self, args, engine, subprocess_check_call, id_generator):
        args.no_verify = False
        hook_name = id_generator()
        subprocess_check_call.side_effect = OSError

        assert do_hook(args, engine, hook_name)

    def test_with_failed_hook(self, args, engine, subprocess_check_call, id_generator):
        args.no_verify = False
        hook_name = id_generator()
        subprocess_check_call.side_effect = CalledProcessError(None, None, None)

        assert not do_hook(args, engine, hook_name)


class InitCallTestCase(object):

    def test_correct_setup_defaults(self, args, engine):
        inputs = ["REPO_NAME", "", "", "", "", "", "", ""]
        input_gen = itertools.islice(inputs, None)

        def input_func(query_str):
            return input_gen.next()

        output_func = lambda x: None

        handle_init_call(
            args,
            engine,
            input_func=input_func,
            output_func=output_func,
        )

        engine.assert_has_calls([
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

    def test_correct_setup(self, id_generator, engine, args):
        inputs = [id_generator() for x in range(8)]
        input_gen = itertools.islice(inputs, None)

        def input_func(query_str):
            return input_gen.next()

        output_func = lambda x: None

        handle_init_call(args, engine, input_func, output_func)

        engine.assert_has_calls([
            mock.call.setup_repository_structure(*inputs)
        ])


class FeatureCallTestCase(object):
    def test_start(self, id_generator, args, engine):
        args.action = "start"
        args.issue_num = None
        args.name = id_generator(chars=string.ascii_letters)
        args.track = False

        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True
            handle_feature_call(args, engine)

            patch.assert_has_calls([
                mock.call(args, engine, "post-feature-start")
            ])

            engine.assert_has_calls([
                mock.call.create_feature(
                    name=args.name,
                    with_tracking=args.track,
                ),
            ])

    def test_start_with_issue_number(self, id_generator, args, engine):
        args.action = "start"
        args.name = id_generator(chars=string.ascii_letters)
        args.issue_num = id_generator(chars=string.digits)
        expected_name = "{}-{}".format(args.issue_number, args.name)
        args.track = False

        handle_feature_call(args, engine)

        engine.assert_has_calls([
            mock.call.create_feature(
                name=expected_name,
                with_tracking=args.track,
            ),
        ])

    def test_work(self, id_generator, args, engine):
        args.action = "work"
        args.issue = None
        args.identifier = id_generator()
        handle_feature_call(args, engine)

        engine.assert_has_calls([
            mock.call.work_feature(name=args.identifier),
        ])

    def test_work_with_issue_num(self, id_generator, args, engine):
        args.action = "work"
        args.issue = True
        args.identifier = id_generator()
        handle_feature_call(args, engine)

        engine.assert_has_calls([
            mock.call.work_feature(issue=args.identifier),
        ])

    def test_publish(self, id_generator, args, engine):
        args.action = "publish"
        args.name = id_generator()
        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True

            handle_feature_call(args, engine)

            patch.assert_has_calls([
                mock.call(args, engine, "pre-feature-publish")
            ])

            engine.assert_has_calls([
                mock.call.publish_feature(name=args.name),
            ])

    def test_publish_failed_hook(self, args, engine):
        args.action = "publish"
        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = False
            handle_feature_call(args, engine)

            assert engine.call_count == 0

    def test_abandon(self, id_generator, args, engine):
        args.action = "abandon"
        args.name = id_generator()
        handle_feature_call(args, engine)
        engine.assert_has_calls([
            mock.call.abandon_feature(name=args.name),
        ])

    def test_accepted(self, id_generator, args, engine):
        args.action = 'accepted'
        args.name = id_generator()
        args.no_delete = False

        handle_feature_call(args, engine)

        engine.assert_has_calls([
            mock.call.accept_feature(
                name=args.name,
                delete_feature_branch=True,
            ),
        ])

    def test_accepted_no_delete(self, id_generator, args, engine):
        args.action = 'accepted'
        args.name = id_generator()
        args.no_delete = True

        handle_feature_call(args, engine)

        engine.assert_has_calls([
            mock.call.accept_feature(
                name=args.name,
                delete_feature_branch=False,
            ),
        ])

    def test_list(self, args, engine):
        args.action = "list"
        handle_feature_call(args, engine)

        engine.assert_has_calls([
            mock.call.list_features(),
        ])

    def test_undefined_action(self, id_generator, args, engine):
        args.action = id_generator()
        with pytest.raises(RuntimeError):
            handle_feature_call(args, engine)


class ReleaseCallTestCase(object):

    def test_start(self, id_generator, args, engine):
        args.action = "start"
        args.name = id_generator()

        with mock.patch('flowhub.core.do_hook') as patch:
            handle_release_call(args, engine)

            patch.assert_has_calls([
                mock.call(args, engine, "post-release-start", args.name),
            ])

            engine.assert_has_calls([
                mock.call.start_release(name=args.name),
            ])

    def test_publish_with_name(self, id_generator, args, engine, create_tag_info_mock):
        args.action = "publish"
        args.no_cleanup = False
        args.name = id_generator()

        with mock.patch('flowhub.core.do_hook') as patch:
            def input_func(query_str):
                return ""

            handle_release_call(args, engine, input_func=input_func)

            patch.assert_has_calls([
                mock.call(args, engine, "pre-release-publish"),
                mock.call().__nonzero__(),  # the if check
                mock.call(args, engine, "post-release-publish", mock.ANY),
            ])

            engine.assert_has_calls([
                mock.call.publish_release(
                    name=args.name,
                    with_delete=not args.no_cleanup,
                    tag_info=create_tag_info_mock.return_value,
                ),
            ])

            create_tag_info_mock.assert_called_once_with(
                args,
                input_func,
                engine.release.name.replace.return_value,
            )

    def test_publish_failed_hook(self, id_generator, args, engine):
        args.action = "publish"
        args.name = id_generator()

        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = False

            handle_release_call(args, engine)

            patch.assert_has_calls([
                mock.call(args, engine, "pre-release-publish"),
            ])

            assert engine.call_count == 0

    def test_contribute(self, args, engine):
        args.action = "contribute"

        handle_release_call(args, engine)

        engine.assert_has_calls([
            mock.call.contribute_release(),
        ])


class HotfixCallTestCase(object):
    def test_start(self, id_generator, args, engine):
        args.action = "start"
        args.name = id_generator()
        args.issue_numbers = []

        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True

            handle_hotfix_call(args, engine)

            patch.assert_has_calls([
                mock.call(
                    args,
                    engine,
                    "post-hotfix-start",
                    args.name,
                ),
            ])

            engine.assert_has_calls([
                mock.call.start_hotfix(
                    name=args.name,
                    issues=args.issue_numbers
                )
            ])

    def test_publish_with_name(self, id_generator, args, engine, create_tag_info_mock):
        args.action = "publish"
        args.name = id_generator()
        args.issue_numbers = []
        with mock.patch('flowhub.core.do_hook') as patch:
            patch.return_value = True

            def input_func(query_str):
                return ""

            handle_hotfix_call(
                args,
                engine,
                input_func=input_func
            )

            patch.assert_has_calls([
                mock.call(args, engine, 'pre-hotfix-publish'),
                mock.call(args, engine, 'post-hotfix-publish', mock.ANY),

            ])

            engine.assert_has_calls([
                mock.call.publish_hotfix(
                    name=args.name,
                    tag_info=create_tag_info_mock.return_value,
                ),
            ])

            create_tag_info_mock.assert_called_once_with(
                args,
                input_func,
                engine.hotfix.name.replace.return_value,
            )

    def test_contribute(self, args, engine):
        args.action = "contribute"

        handle_hotfix_call(args, engine)

        engine.assert_has_calls([
            mock.call.contribute_hotfix(),
        ])


class CleanupCallTestCase(object):
    OPTIONS = ['t', 'u', 'r']

    def test_option_combinations(self, args, engine):

        for l in range(1, len(self.OPTIONS)+1):

            for combo in itertools.combinations(self.OPTIONS, l):
                # reset the chosen options
                for o in self.OPTIONS:
                    setattr(args, o, False)
                args.all = False

                print combo
                for choice in combo:
                    setattr(args, choice, True)

                handle_cleanup_call(args, engine)

                engine.assert_has_calls([
                    mock.call.cleanup_branches(targets=''.join(combo))
                ])

    def test_all(self, args, engine):
        for o in self.OPTIONS:
            setattr(args, o, False)
        args.all = True

        handle_cleanup_call(args, engine)

        engine.assert_has_calls([
            mock.call.cleanup_branches(targets='tur')
        ])

    def test_no_targets(self, args, engine):
        for o in self.OPTIONS:
            setattr(args, o, False)
        args.all = False

        handle_cleanup_call(args, engine)

        assert engine.call_count == 0


class IssueCallTestCase(object):
    @pytest.mark.parametrize("create_branch", (True, False))
    def test_start(self, create_branch, args, engine):
        args.action = "start"
        args.labels = False
        args.create_branch = create_branch

        handle_issue_call(args, engine)

        engine.assert_has_calls([
            mock.call.open_issue(
                title=args.title,
                labels=None,
                create_branch=args.create_branch,
            )
        ])

    @pytest.mark.parametrize("create_branch", (True, False))
    def test_start_with_labels(self, create_branch, id_generator, args, engine):
        args.action = "start"
        args.labels = ",".join((id_generator() for x in range(5)))
        args.create_branch = create_branch

        handle_issue_call(args, engine)

        engine.assert_has_calls([
            mock.call.open_issue(
                title=args.title,
                labels=args.labels.split(','),
                create_branch=args.create_branch,
            )
        ])
