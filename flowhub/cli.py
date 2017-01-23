#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
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

import argparse
import argcomplete

from flowhub.base import Base
from flowhub.exceptions import Abort, HookFailure
from flowhub.engine import Engine, DuplicateFeature, NeedsAuthorization, NotAFeatureBranch
from flowhub.utilities import future_proof_print

__version__ = '1.0.0'


class CLI(Base):
    def __init__(self, input_func=None, output_func=None):
        if input_func is None:
            input_func = raw_input
        if output_func is None:
            output_func = future_proof_print
        self._input = input_func
        self._output = output_func
        self._offline_engine = Engine(
            offline=True,
            verbosity=-1,
            repo_directory='.',
            cli=self,
            skip_hooks=True,
        )

    def emit_message(self, msg):
        self._output(msg)

    def ingest_message(self, msg):
        return self._input(msg)

    def build_engine(self, args):
        try:
            return Engine(
                offline=args.offline,
                verbosity=args.verbosity,
                repo_directory='.',
                cli=self,
                skip_hooks=args.no_verify,
            )
        except NeedsAuthorization:
            self._offline_engine.get_authorization()
            return self.build_engine(args)
        except Abort:
            raise

    def build_parser(self, parser):
        parser.add_argument(
            '-v',
            '--verbosity',
            action="store",
            type=int,
            default=0,
        )
        parser.add_argument(
            '--offline',
            action='store_true',
            default=False,
            help='do not talk to a remote service',
        )
        parser.add_argument(
            '--no-verify',
            action='store_true',
            default=False,
            help='do not call any hooks',
        )
        parser.add_argument(
            '--version',
            action='version',
            version=('flowhub v{}'.format(__version__)),
        )

        subparsers = parser.add_subparsers(dest="subparser")
        self._build_init_parser(
            subparsers.add_parser(
                'init',
                help="set up a repository to use flowhub",
            ),
        )
        self._build_feature_parser(
            subparsers.add_parser(
                'feature',
                help="do feature-related things",
            ),
        )
        self._build_release_parser(
            subparsers.add_parser(
                'release',
                help="do release-related things",
            ),
        )
        self._build_hotfix_parser(
            subparsers.add_parser(
                'hotfix',
                help="do hotfix-related things",
            ),
        )

    def _build_init_parser(self, parser):
        pass

    def _build_feature_parser(self, parser):
        feature_subs = parser.add_subparsers(dest='action')
        branches = self._offline_engine.all_local_branches()
        FEATURE_PREFIX = self._offline_engine.get_prefixes()['feature']
        completers = {}

        # flowhub feature start ...
        fstart = feature_subs.add_parser(
            'start',
            help="start a new feature branch",
        )
        fstart.add_argument('name', help="name of the feature")
        fstart.add_argument(
            '--track',
            action='store_true', default=False,
            help="set up a tracking branch on your github immediately.",
        )
        fstart.add_argument(
            '-i', '--issue-number',
            type=int,
            action='store', default=None,
            help="prepend an issue number to the feature name",
        )

        # flowhub feature work ...
        fwork = feature_subs.add_parser(
            'work',
            help="switch to a different feature (by name)",
        )
        fwork_name = fwork.add_argument(
            'identifier',
            help="name of feature to switch to",
        )
        completers[fwork_name] = [
            branch.name.split(FEATURE_PREFIX)[1] for branch in branches
            if branch.name.startswith(FEATURE_PREFIX)
        ]
        fwork.add_argument(
            '--issue', '-i',
            action='store_true', default=False,
            help='switch to a branch by issue number instead of by name')

        # flowhub feature publish ...
        fpublish = feature_subs.add_parser(
            'publish',
            help="send the current feature branch to origin and create a pull-request",
        )
        fpublish_name = fpublish.add_argument(
            'name',
            nargs='?',
            default=None,
            help='name of feature to publish. If not given, uses current feature',
        )
        completers[fpublish_name] = [
            branch.name.split(FEATURE_PREFIX)[1] for branch in branches
            if branch.name.startswith(FEATURE_PREFIX)
        ]

        # flowhub feature accepted ...
        faccepted = feature_subs.add_parser(
            'accepted',
            help="declare that a feature was accepted into the trunk",
        )
        faccepted_name = faccepted.add_argument(
            'name',
            nargs='?',
            default=None,
            help="name of the accepted feature. If not given, assumes current feature",
        )
        completers[faccepted_name] = [
            branch.name.split(FEATURE_PREFIX)[1] for branch in branches
            if branch.name.startswith(FEATURE_PREFIX)
        ]
        faccepted.add_argument(
            '--no-delete',
            action='store_true', default=False,
            help="don't delete the accepted feature branch",
        )
        faccepted.add_argument(
            '--merge',
            action='store_true', default=False,
            help="feature should be merged into development branch as well",
        )

        self._setup_parser_completers(completers)

    def _build_release_parser(self, parser):
        release_subs = parser.add_subparsers(dest='action')

        rstart = release_subs.add_parser(
            'start',
            help="start a new release branch",
        )
        rstart.add_argument(
            'name',
            help="name (and tag) of the release branch.",
        )

        release_subs.add_parser(
            'stage',
            help="send a release branch to a staging environment",
        )

        rpublish = release_subs.add_parser(
            'publish',
            help="publish a release branch to production and trunk",
        )
        rpublish.add_argument(
            'name',
            nargs='?',
            help="name of release to publish. if not specified, current branch is assumed.",
        )
        rpublish.add_argument(
            '--no-cleanup',
            action='store_true',
            default=False,
            help="do not delete the release branch after a successful publish",
        )

    def _build_hotfix_parser(self, parser):
        pass

    def _setup_parser_completers(self, completers):
        for argument, completion_values in completers.items():
            argument.completer = argcomplete.completers.ChoicesCompleter(
                completion_values,
            )

    def handle_invocation(self, args):
        self._verbosity = args.verbosity
        try:
            summary = getattr(
                self,
                "handle_{}_invocation".format(args.subparser),
                self.handle_unknown_invocation
            )(args)
        except Abort:
            raise
        except Exception:
            import traceback
            traceback.print_exc()
        else:
            if len(summary) != 0:
                summary = ['\n\033[1;37;40mSummary of actions:\033[1;37;40m'] + summary
                self._output(
                    "\n - ".join(
                        map(
                            lambda s: "{color}{msg}{reset}".format(
                                color='\033[1;31;40m' if hasattr(s, 'type') and s.type == 'bad' else '\033[0;37;40m',
                                msg=s,
                                reset='\033[1;37;40m'
                            ),
                            summary
                        ),
                    ),
                )

    def handle_init_invocation(self, args):
        self.print_at_verbosity({3: 'handling init'})
        engine = self._offline_engine
        engine._verbosity = self._verbosity

        remote_type = self._input('Where is your remote? ({}): '.format(', '.join(engine.known_connectors())))
        if remote_type not in engine.known_connectors():
            raise RuntimeError('unsupported service: {}'.format(remote_type))

        repo_name = self._input('Name of your repo: ')
        origin_label = self._input('Name of your remote [origin]: ') or 'origin'
        canon_label = self._input('Name of the organization remote [canon]: ') or 'canon'
        master_label = self._input('Name of the stable branch [master]: ') or 'master'
        development_label = self._input('Name of the development branch [develop]: ') or 'develop'
        feature_label = self._input('Prefix for feature branches [feature/]: ') or 'feature/'
        release_label = self._input('Prefix for release branches [release/]: ') or 'release/'
        hotfix_label = self._input('Prefix for hotfix branches [hotfix/]: ') or 'hotfix/'

        engine.record_repo_structure(
            remote_type=remote_type,
            repo_name=repo_name,
            origin_label=origin_label,
            canon_label=canon_label,
            master_label=master_label,
            development_label=development_label,
            feature_label=feature_label,
            release_label=release_label,
            hotfix_label=hotfix_label,
        )

        return engine.get_summary()

    def handle_feature_invocation(self, args):
        self.print_at_verbosity({3: 'handling feature'})
        engine = self.build_engine(args)

        if args.action == 'start':
            try:
                engine.start_feature(
                    name=args.name,
                    issue_number=args.issue_number,
                    with_tracking=args.track,
                    fetch_development=True,
                )
            except DuplicateFeature:
                self._output('Feature {} is already in-progress! You should abandon it first.'.format(args.name))

        elif args.action == 'work':
            engine.switch_to_feature(
                identifier=args.identifier,
            )

        elif args.action == 'publish':
            try:
                engine.publish_feature(
                    name=args.name,
                )
            except NotAFeatureBranch as error:
                self._output('{} is not a feature branch. Please provide a feature branch as an argument, or switch to the feature branch you wish to publish.'.format(error.message))
            except HookFailure as error:
                self._output('operation aborted by hook {}'.format(error.message))
        elif args.action == 'accepted':
            try:
                engine.accept_feature(
                    name=args.name,
                    should_delete_branch=not args.no_delete,
                    should_merge_into_development=not args.merge,
                )
            except NotAFeatureBranch as error:
                self._output('{} is not a feature branch. Please provide a feature branch as an argument, or switch to the feature branch you wish to accept.'.format(error.message))
        else:
            raise RuntimeError("Unimplemented command for features: {}".format(args.action))

        return engine.get_summary()

    def handle_release_invocation(self, args):
        self.print_at_verbosity({3: 'handling release'})
        engine = self.build_engine(args)
        if args.action == 'start':
            engine.start_release(args.name)
        elif args.action == 'stage':
            self._output("Gosh, sure be nice if this command did anything...")
        elif args.action == 'publish':
            engine.publish_release()
        return engine.get_summary()

    def handle_unknown_invocation(self, args):
        self._output('unrecognized command!')
        return []


def run():
    parser = argparse.ArgumentParser()

    cli = CLI()
    cli.build_parser(parser)
    args = parser.parse_args()

    cli.handle_invocation(args)


if __name__ == "__main__":
    run()
