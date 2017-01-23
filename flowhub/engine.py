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
import subprocess
import tempfile
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
    def __init__(self, offline, verbosity, repo_directory, cli):
        self._offline = offline
        self._verbosity = verbosity
        self._cli = cli

        self._summary = []
        self._repo = git.Repo(repo_directory)
        self._config = Configurator(self._repo)
        self._connector_factory = ConnectorFactory(self._config, self)

        if not self.is_authorized():
            raise NeedsAuthorization

    def request_output(self, msg):
        self._cli.emit_message(msg)

    def request_input(self, msg):
        return self._cli.ingest_message(msg)

    def add_to_summary_items(self, msg, type='good'):
        self._summary += [SummaryLine(msg, type)]

    def get_authorization(self):
        # normally we'd use self.connector, but we're likely to seek
        # authorization from the 'offline' version of the engine --- so we
        # regretfully violate the law of demeter here to go after the connector
        # we really care about.
        with self._config.reader() as reader:
            connector_type = reader.flowhub.structure.connectorType

        self._connector_factory.connector_for(connector_type).get_authorization()

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
        if self._offline:
            return None
        self._find_remote(remote_name).fetch()
        self.add_to_summary_items('Fetched latest changes from {}'.format(remote_name))

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
                self.add_to_summary_items('Created branch {}'.format(name))
            else:
                branch = self._repo.create_head(name, parent)
                self.add_to_summary_items('Created branch {} off of {}'.format(name, parent.name))

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
        self.add_to_summary_items('Checked out branch {}'.format(identifier))

    def push_to_remote(self, name, remote_name, set_upstream):
        if self._offline:
            return None
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
            set_upstream=set_upstream,
        )

        if not existed_already:
            self.add_to_summary_items(
                "Created a remote {}branch on {} for {}".format(
                    'tracking' if set_upstream else '',
                    remote_name,
                    name,
                ),
            )
        elif set_upstream:
            self.add_to_summary_items(
                'Set {} to track {} on {}'.format(
                    name,
                    name,
                    remote_name,
                ),
            )

        if had_new_commits and existed_already:
            self.add_to_summary_items(
                "Pushed new commits to {}".format(remote_name),
            )

    def update_from_remote(self, branch_name, remote_name):
        if self._offline:
            return None
        self.fetch_remote(remote_name)
        remote = self._find_remote(remote_name)
        outdated_branch = self._find_branch(branch_name)

        outdate_branch.checkout()
        self._repo.git.merge(
            '{}/{}'.format(remote, outdated_branch),
        )
        self.add_to_summary_items(
            'Updated {} from {}'.format(branch_name, remote_name)
        )

    def merge_into(self, branch_name, target_branch_name):
        self.switch_to_branch(target_branch_name)
        self._repo.git.merge(branch_name)
        self.add_to_summary(
            "Merged {} into {}".format(branch_name, target_branch_name),
        )

    def delete_branch(self, branch_name):
        self.repo.delete_head(
            branch_name,
        )
        self.add_to_summary_items(
            "Deleted {} from local repository".format(branch_name),
        )

        if not self._offline:
            self.origin.push(
                branch_name,
                delete=True,
            )
            self.add_to_summary_items(
                "Deleted {} from {}".format(branch_name, self.origin),
            )

    def _find_feature_branch_by_name(self, name):
        FEATURE_PREFIX = self.get_prefixes()['feature']
        # no name means the current branch
        if name is None:
            name = self.current_branch().name

        branch_name = "{}{}".format(
            FEATURE_PREFIX,
            name.replace(FEATURE_PREFIX, ''),
        )

        if self._find_branch(branch_name) is None:
            return None

        return branch_name

    def accept_feature(
        self,
        name,
        should_delete_branch,
        should_merge_into_development,
    ):
        if name is None:
            return_branch = self.develop.name
        else:
            return_branch = self.current_branch().name

        branch_name = self._find_feature_branch_by_name(name)
        if branch_name is None:
            raise NotAFeatureBranch(name)
        # update development branch with latest from canon
        self.update_from_remote(self.develop.name, self.canon.name)

        if should_merge_into_development:
            self.merge_into(branch_name, self.develop.name)

        if should_delete_branch:
            self.delete_branch(branch_name)

        self.switch_to_branch(return_branch)

    def publish_feature(self, name):
        branch_name = self._find_feature_branch_by_name(name)
        if branch_name is None:
            raise NotAFeatureBranch(name)

        self.push_to_remote(branch_name, self.origin.name, True)

        if not self._offline:
            request_results = self.connector.make_request(
                base_branch_name=self.develop.name,
                branch_name=branch_name,
                remote_name=self.origin.name,
            )

            if request_results.success:
                if request_results.new:
                    self.add_to_summary_items(
                        textwrap.dedent("""
                            New pull request created: {} into {}
                            \turl: {}""".format(
                                name,
                                self.develop.name,
                                request_results.url,
                            )
                        )[1:],
                    )
                else:
                    self.add_to_summary_items(
                        textwrap.dedent("""
                            New commits added to existing request
                            \turl: {}""".format(
                                request_results.url,
                            )
                        )[1:],
                    )
            else:
                self.add_to_summary_items(
                    "Request to {} was unsuccessful.".format(self.connector.service_name()),
                )

    def abandon_feature(self):
        pass

    def create_issue(self):
        labels = []
        title = self.request_input("Title for this issue: ")
        descriptor_file = tempfile.NamedTemporaryFile(delete=False)
        descriptor_file.file.write(
            "\n\n# Write your description above. Remember - you can use Github markdown syntax!"
        )

        self.print_at_verbosity({3: 'temp file: {}'.format(descriptor_file.name)})
        descriptor_file.close()

        try:
            editor_result = subprocess.check_call(
                "$EDITOR {}".format(descriptor_file.name),
                shell=True
            )
        except OSError:
            self.print_at_verbosity({2: "Hmm...are you on Windows?"})
            editor_result = 126

        self.print_at_verbosity({4: 'result of $EDITOR: {}'.format(editor_result)})

        if editor_result == 0:
            # Re-open the file to get new contents...
            fnew = open(descriptor_file.name, 'r')
            # and remove the first line
            body = fnew.readlines()
            if body[-1].startswith('# Write your description'):
                body = body[:-1]

            body = "".join(body)

            fnew.close()
        else:
            body = self.request_input(
                "Description (remember, you can use GitHub markdown):\n"
            )

        self.print_at_verbosity({4: 'issue description: {}'.format(body)})

        result = self.connector.open_issue(title, body, labels)

        self.add_to_summary_items(
            textwrap.dedent("""
                Opened issue #{number}: {title}{labels}
                \turl: {url}""".format(
                    number=result.number,
                    title=title,
                    labels='\n\t[{}]'.format(' '.join(labels)) if labels else '',
                    url=result.url,
                ),
            ),
        )

        return result

    def get_summary(self):
        # don't let the outside world muck with our summary
        return [x for x in self._summary]
