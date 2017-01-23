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
import os
import subprocess
import tempfile
import textwrap

import git

from flowhub.base import Base
from flowhub.config.configurator import Configurator
from flowhub.connectors.connector_factory import ConnectorFactory
from flowhub.exceptions import HookFailure


class DuplicateFeature(StandardError):
    pass


class NotAFeatureBranch(StandardError):
    pass


class NotAReleaseBranch(StandardError):
    pass


class NeedsAuthorization(StandardError):
    pass


class ReleaseExists(StandardError):
    pass


class SummaryLine(namedtuple('SummaryLineParent', ['msg', 'type'])):
    def __str__(self):
        return self.msg


class Engine(Base):
    def __init__(self, offline, verbosity, repo_directory, cli, skip_hooks):
        self._offline = offline
        self._verbosity = verbosity
        self._cli = cli
        self._skip_hooks = skip_hooks

        self._summary = []
        self._repo = git.Repo(repo_directory)
        self._config = Configurator(self._repo)
        self._connector_factory = ConnectorFactory(self._config, self)

        if not self.is_authorized():
            raise NeedsAuthorization

    def request_output(self, msg):
        self._cli.emit_message(msg)

    def do_hook(self, hook_name, *hook_args):
        if self._skip_hooks:
            return True

        try:
            hook_args = tuple(str(a) for a in hook_args)
            subprocess.check_call(
                (os.path.join(self._repo.git_dir, 'hooks', hook_name),) + hook_args,
            )
            return True
        except OSError as e:
            self.print_at_verbosity({2: "No such hook: {}".format(hook_name)})
            self.print_at_verbosity({4: "{}".format(e)})
            return True
        except subprocess.CalledProcessError:
            return False

    def request_input(self, msg):
        return self._cli.ingest_message(msg)

    def add_to_summary_items(self, msg, type='good'):
        self._summary += [SummaryLine(msg, type)]

    @property
    def connector_type(self):
        with self._config.reader() as reader:
            return reader.flowhub.structure.connectorType

    def get_authorization(self):
        # normally we'd use self.connector, but we're likely to seek
        # authorization from the 'offline' version of the engine --- so we
        # regretfully violate the law of demeter here to go after the connector
        # we really care about.
        self._connector_factory.connector_for(self.connector_type).get_authorization()

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

        return self._connector_factory.connector_for(self.connector_type)

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

        self.do_hook('post-feature-start', branch_name)

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

        return had_new_commits

    def update_from_remote(self, branch_name, remote_name):
        if self._offline:
            return None
        self.fetch_remote(remote_name)
        remote = self._find_remote(remote_name)
        outdated_branch = self._find_branch(branch_name)

        outdated_branch.checkout()
        self._repo.git.merge(
            '{}/{}'.format(remote, outdated_branch),
        )
        self.add_to_summary_items(
            'Updated {} from {}'.format(branch_name, remote_name)
        )

    def merge_into(self, branch_name, target_branch_name):
        self.switch_to_branch(target_branch_name)
        self._repo.git.merge(branch_name)
        self.add_to_summary_items(
            "Merged {} into {}".format(branch_name, target_branch_name),
        )

    def delete_branch(self, branch_name, should_delete_from_canon=False):
        self._repo.delete_head(
            branch_name,
        )
        self.add_to_summary_items(
            "Deleted {} from local repository".format(branch_name),
        )

        if not self._offline:
            if not should_delete_from_canon:
                remote = self.origin
            else:
                remote = self.canon

            remote.push(
                branch_name,
                delete=True,
            )
            self.add_to_summary_items(
                "Deleted {} from {}".format(branch_name, remote.name),
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
            self.push_to_remote(branch_name, self.canon.name, False)
            if not self._offline:
                result = self.connector.close_request(branch_name)
                if result.success:
                    self.add_to_summary_items(
                        "Request on {} closed.".format(self.connector.service_name()),
                    )
                else:
                    self.add_to_summary_items(
                        "Request on {} could not be closed!".format(self.connector.service_name()),
                        'bad'
                    )

        if should_delete_branch:
            self.delete_branch(branch_name)

        self.switch_to_branch(return_branch)

    def publish_feature(self, name):
        branch_name = self._find_feature_branch_by_name(name)
        if branch_name is None:
            raise NotAFeatureBranch(name)

        if not self.do_hook('pre-feature-publish', branch_name):
            raise HookFailure('pre-feature-publish')

        already_tracking = self._find_branch(branch_name).tracking_branch is not None
        had_new_commits = self.push_to_remote(branch_name, self.origin.name, not already_tracking)

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
                elif had_new_commits:
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
                    'bad',
                )

    def abandon_feature(self):
        pass

    def start_release(self, name):
        # git fetch canon
        # if git branch-exists canon /^release/ then exit 1
        # git checkout -b release-prefix+release_name canon/develop
        RELEASE_PREFIX = self.get_prefixes()['release']
        if self._offline:
            self.print_at_verbosity({0: 'In offline mode, changes will only be made locally.'})
            existing_releases = [
                x for x in self._repo.branches
                if x.name.startswith(RELEASE_PREFIX)
            ]
            base_branch = self.develop.name
        else:
            self.fetch_remote(self.canon.name)
            existing_releases = {
                x for x in self.canon.refs
                if x.name.startswith(RELEASE_PREFIX)
            } | {
                x for x in self._repo.branches
                if x.name.startswith(RELEASE_PREFIX)
            }
            base_branch = self._find_remote_branch(self.canon.name, self.develop.name)

        if len(existing_releases) != 0:
            raise ReleaseExists(existing_releases.pop())

        branch_name = "{}{}".format(
            RELEASE_PREFIX,
            name.replace(RELEASE_PREFIX, ''),
        )
        self.print_at_verbosity({0: 'Creating a new release branch...'})
        self.create_branch(branch_name, base_branch)

        if not self._offline:
            self.push_to_remote(branch_name, self.canon.name, True)

        self.switch_to_branch(branch_name)
        self.do_hook('post-release-start', branch_name)

    def stage_release(self):
        pass

    def _get_long_form_input(self, file_prompt, input_prompt):
        descriptor_file = tempfile.NamedTemporaryFile(delete=False)
        descriptor_file.file.write(
            "\n\n{}".format(file_prompt)
        )
        self.print_at_verbosity({3: 'temp file: {}'.format(descriptor_file.name)})
        descriptor_file.close()

        body, long_form_successful = self._cli.ingest_long_form_message(descriptor_file)
        # a successful long-form body will be a list of strings
        if long_form_successful:
            # be cautious here, in case the user removed our hint line
            # themselves
            if body[-1].startswith('#'):
                body = body[:-1]
            body = "".join(body)

        return body

    def publish_release(self):
        # git fetch canon
        # git checkout master
        # git merge canon/master
        # git merge --no-ff release/...
        # git tag ... ...
        # git checkout develop
        # git merge canon/develop
        # git merge --no-ff canon/master
        # git push canon
        # git push --tags canon
        # git branch -d release/...
        RELEASE_PREFIX = self.get_prefixes()['release']
        branch_name = self.current_branch().name

        if not branch_name.startswith(RELEASE_PREFIX):
            raise NotAReleaseBranch(branch_name)

        self.do_hook('pre-release-publish', branch_name)

        if self._offline:
            self.print_at_verbosity({0: 'In offline mode, changes will only be made locally.'})
        else:
            self.fetch_remote(self.canon.name)

        self.master.checkout()
        self._repo.git.merge(
            "{}/{}".format(self.canon.name, self.master.name),
        )
        self._repo.git.merge(
            branch_name,
            no_ff=True,
        )
        self.add_to_summary_items(
            "Branch {} merged into {}".format(branch_name, self.master.name),
        )

        default_tag_label = branch_name.replace(RELEASE_PREFIX, '')
        tag_label = self._cli.ingest_message("Tag label [{}]: ".format(default_tag_label)) or default_tag_label
        tag_description = self._get_long_form_input(
            "# Write your tag description above.",
            "Tag message: ",
        )
        self.create_tag(self.master.name, tag_label, tag_description)

        self.develop.checkout()
        self._repo.git.merge(
            "{}/{}".format(self.canon.name, self.develop.name),
        )
        self._repo.git.merge(
            self.master,
            no_ff=True,
        )
        self.add_to_summary_items(
            "Branch {} merged into {}".format(
                self.master.name,
                self.develop.name,
            ),
        )

        self.canon.push()
        self.canon.push(tags=True)

        self.delete_branch(branch_name, should_delete_from_canon=True)

        self.switch_to_branch(self.develop.name)

    def create_tag(self, target_branch_name, label, description):
        self._repo.create_tag(
            path=label,
            ref=self._find_branch(target_branch_name),
            message=description,
        )

        self.add_to_summary_items(
            "New tag ({}) created at {}'s tip.".format(label, target_branch_name),
        )

    def create_issue(self):
        labels = []
        title = self.request_input("Title for this issue: ")

        body = self._get_long_form_input(
            "# Write your description above. Remember - you can use Github markdown syntax!",
            "Description (you can use Github markdown syntax):",
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
                )[1:],
            ),
        )

        return result

    def get_summary(self):
        # don't let the outside world muck with our summary
        return [x for x in self._summary]
