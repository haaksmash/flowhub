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
from collections import namedtuple
import textwrap

import git

from flowhub.base import Base
from flowhub.config.configurator import Configurator
from flowhub.connectors.connector_factory import ConnectorFactory


class DuplicateFeature(StandardError):
    pass


class NotAFeatureBranch(StandardError):
    pass


class NeedsAuthorization(StandardError):
    pass


class SummaryLine(namedtuple('SummaryLineParent', ['msg', 'type'])):
    def __str__(self):
        return self.msg


class Engine(Base):
    def __init__(self, offline, verbosity, output, repo_directory):
        self._offline = offline
        self._verbosity = verbosity
        self._output = output

        self._summary = []
        self._repo = git.Repo(repo_directory)
        self._config = Configurator(self._repo)
        self._connector_factory = ConnectorFactory(self._config)

        if not self.is_authorized():
            raise NeedsAuthorization

    def get_authorization(self, output_func, input_func):
        # normally we'd use self.connector, but we're likely to seek
        # authorization from the 'offline' version of the engine --- so we
        # regretfully violate the law of demeter here to go after the connector
        # we really care about.
        with self._config.reader() as reader:
            connector_type = reader.flowhub.structure.connectorType

        self._connector_factory.connector_for(connector_type).get_authorization(
            output_func, input_func
        )

    def is_authorized(self):
        return self.connector.is_authorized()

    def known_connectors(self):
        return self._connector_factory.known_connectors()

    def record_repo_structure(
        self,
        remote_type,
        repo_name,
        origin_label,
        canon_label,
        master_label,
        development_label,
        feature_label,
        release_label,
        hotfix_label,
    ):
        self.print_at_verbosity({
            2: 'begin repo setup',
            3: """
                begin repo setup
                  connector is {}
                  origin repo is {}
                  canon repo is {}
                  master branch is {}
                  development branch is {}
                  feature prefix is {}
                  release prefix is {}
                  hotfix prefix is {}
                """.format(remote_type, origin_label, canon_label, master_label, development_label, feature_label, release_label, hotfix_label),
        })

        with self._config.writer() as writer:
            structure_section_name = 'flowhub "structure"'
            if not writer.has_section(structure_section_name):
                self.print_at_verbosity({
                    3: "adding config section for flowhub structure"
                })
                writer.add_section(structure_section_name)

            else:
                self.print_at_verbosity({4: 'flowhub structure section found'})

            writer.set(structure_section_name, 'connectorType', remote_type)
            writer.set(structure_section_name, 'name', repo_name)

            writer.set(structure_section_name, 'origin', origin_label)
            writer.set(structure_section_name, 'canon', canon_label)

            writer.set(structure_section_name, 'master', master_label)
            self.create_branch(master_label, parent=None)

            writer.set(structure_section_name, 'develop', development_label)
            self.create_branch(development_label, parent=self._find_branch(master_label))

            prefix_section_name = 'flowhub "prefix"'
            if not writer.has_section(prefix_section_name):
                self.print_at_verbosity({
                    3: "adding config section for flowhub prefixes"
                })
                writer.add_section(prefix_section_name)

            else:
                self.print_at_verbosity({4: 'flowhub prefix section found'})

            writer.set(prefix_section_name, 'feature', feature_label)
            writer.set(prefix_section_name, 'release', release_label)
            writer.set(prefix_section_name, 'hotfix', hotfix_label)

    def all_local_branches(self):
        return [b for b in self._repo.branches]

    def current_branch(self):
        return self._repo.head.ref

    def get_prefixes(self):
        with self._config.reader() as reader:
            return {
                'feature': reader.flowhub.prefix.feature,
                'hotfix': reader.flowhub.prefix.hotfix,
                'release': reader.flowhub.prefix.release,
            }

    def fetch_remote(self, remote_name):
        self._find_remote(remote_name).fetch()
        self._summary += [SummaryLine('Fetched latest changes from {}'.format(remote_name), 'good')]

    def _find_branch(self, name):
        return getattr(self._repo.heads, name, None)

    def _find_remote(self, name):
        return getattr(self._repo.remotes, name, None)

    def _find_remote_branch(self, remote_name, branch_name):
        remote = self._find_remote(remote_name)
        if remote is None:
            return None

        return getattr(remote.refs, branch_name, None)

    def create_branch(self, name, parent):
        if getattr(self._repo.heads, name, None) is None:
            self.print_at_verbosity({3: 'creating branch {} off of {}'.format(name, parent)})
            if parent is None:
                branch = self._repo.create_head(name)
                self._summary += [SummaryLine('Created branch {}'.format(name), 'good')]
            else:
                branch = self._repo.create_head(name, parent)
                self._summary += [SummaryLine('Created branch {} off of {}'.format(name, parent.name), 'good')]

            return branch
        else:
            self.print_at_verbosity({4: 'branch {} exists already'.format(name)})
            return None

    @property
    def connector(self):
        if self._offline:
            return self._connector_factory.connector_for('noop')

        with self._config.reader() as reader:
            connector_type = reader.flowhub.structure.connectorType

        return self._connector_factory.connector_for(connector_type)

    @property
    def master(self):
        with self._config.reader() as reader:
            return self._find_branch(reader.flowhub.structure.master)

    @property
    def develop(self):
        with self._config.reader() as reader:
            return self._find_branch(reader.flowhub.structure.develop)

    @property
    def origin(self):
        with self._config.reader() as reader:
            return self._find_remote(reader.flowhub.structure.origin)

    @property
    def canon(self):
        with self._config.reader() as reader:
            return self._find_remote(reader.flowhub.structure.canon)

    def create_pull_request(self):
        pass

    def start_feature(
        self,
        name,
        issue_number,
        with_tracking,
        fetch_development,
    ):
        if fetch_development:
            self.fetch_remote(self.origin.name)

        branch_name = "{}{}".format(
            self.get_prefixes()['feature'],
            name,
        )
        if self.create_branch(branch_name, self.develop) is None:
            raise DuplicateFeature('duplicate feature: {}'.format(name))

        self.switch_to_branch(branch_name)

        if not self._offline and with_tracking:
            self.push_to_remote(branch_name, self.origin.name, True)

    def switch_to_branch(self, identifier):
        branch = self._find_branch(identifier)

        branch.checkout()
        self._summary += [SummaryLine('Checked out branch {}'.format(identifier), 'good')]

    def push_to_remote(self, name, remote_name, set_upstream):
        self.print_at_verbosity({2: 'sending changes on {} to {}'.format(name, remote_name)})
        remote = self._find_remote(remote_name)
        local_branch = self._find_branch(name)
        remote_branch = self._find_remote_branch(remote_name, name)

        existed_already = remote_branch is not None
        had_new_commits = (not existed_already) or \
            remote_branch.commit.hexsha != local_branch.commit.hexsha

        self._repo.git.push(
            remote,
            name,
            set_upstream=set_upstream
        )

        if not existed_already:
            self._summary += [
                SummaryLine("Created a remote {}branch on {} for {}".format(
                    'tracking' if set_upstream else '',
                    remote_name,
                    name,
                ), 'good'),
            ]
        elif set_upstream:
            self._summary += [
                SummaryLine('Set {} to track {} on {}'.format(
                    name,
                    name,
                    remote_name,
                ), 'good'),
            ]

        if had_new_commits and existed_already:
            self._summary += [
                SummaryLine("Pushed new commits to {}".format(remote_name), 'good'),
            ]

    def accept_feature(self):
        pass

    def publish_feature(self, name):
        FEATURE_PREFIX = self.get_prefixes()['feature']
        # no name means publish the current branch
        if name is None:
            name = self.current_branch().name

        branch_name = "{}{}".format(
            FEATURE_PREFIX,
            name.replace(FEATURE_PREFIX, ''),
        )

        if self._find_branch(branch_name) is None:
            raise NotAFeatureBranch(name)

        self.push_to_remote(branch_name, self.origin.name, True)

        if not self._offline:
            request_results = self.connector.make_request(
                base_branch_name=self.develop.name,
                branch_name=name,
                remote_name=self.origin.name,
            )

            if request_results.success:
                if request_results.new:
                    self._summary += [
                        SummaryLine(
                            textwrap.dedent("""
                                New pull request created: {} into {}
                                \turl: {}
                            """.format(
                                name,
                                self.develop.name,
                                request_results.url,
                            ))[1:],
                            'good',
                        ),
                    ]
                else:
                    self._summary += [
                        SummaryLine(
                            textwrap.dedent("""
                                New commits added to existing request
                                \turl: {}
                            """.format(
                                request_results.url,
                            ))[1:],
                            'good',
                        ),
                    ]
            else:
                self._summary += [
                    SummaryLine(
                        "Request to {} was unsuccessful.".format(self.connector.service_name()),
                        'bad',
                    ),
                ]

    def abandon_feature(self):
        pass

    def get_summary(self):
        # don't let the outside world muck with our summary
        return [x for x in self._summary]
