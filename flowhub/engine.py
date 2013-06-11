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

import getpass
import re
import subprocess
import tempfile
import warnings

import git
from github import Github, GithubException

from configurator import Configurator, ImproperlyConfigured
from decorators import with_summary
from managers import TagInfo
from managers.feature import FeatureManager
from managers.hotfix import HotfixManager
from managers.pull_request import PullRequestManager
from managers.release import ReleaseManager


class NoSuchObject(Exception):
    pass

class NoSuchBranch(NoSuchObject):
    pass
class NoSuchRemote(NoSuchObject):
    pass


def online_only(method):
    def wrapper(self, *args, **kwargs):
        if self.offline:
            print "not available offline"
            return False

        return method(self, *args, **kwargs)

    return wrapper


class Engine(object):
    def __init__(self, debug=0, INIT=False, offline=False):
        self.DEBUG = debug
        if self.DEBUG > 2:
            print "initing engine"

        # assume flowhub is called from within a git repository
        self._repo = git.Repo(".")
        self._cr = Configurator(self._repo.config_reader())

        self._gh = None

        self.offline = offline
        if not self.offline:
            if self.DEBUG > 0:
                print "Authorizing engine..."
            if not self.do_auth():
                print "Authorization failed! Exiting."
                return

            try:
                self._gh_repo = self._gh.get_user().get_repo(
                    self._cr.flowhub.structure.name
                )
            except GithubException:
                raise ImproperlyConfigured(
                    "No repo with given name: {}".format(
                        self._cr.flowhub.structure.name,
                    )
                )

            if self._gh.rate_limiting[0] < 100:
                warnings.warn(
                    "You are close to exceeding your GitHub access rate; {} left out of {}".format(
                        *self._gh.rate_limiting
                    )
                )
        else:
            if self.DEBUG > 0:
                print "Skipping auth - GitHub accesses will fail."

        if not INIT:
            self.feature_manager = FeatureManager(
                debug=self.DEBUG,
                prefix=self._cr.flowhub.prefix.feature,
                origin=self.origin,
                canon=self.canon,
                master=self.master,
                develop=self.develop,
                release=self.release,
                hotfix=self.hotfix,
                repo=self._repo,
                gh=self._gh,
                offline=self.offline,
            )

            self.release_manager = ReleaseManager(
                debug=self.DEBUG,
                prefix=self._cr.flowhub.prefix.release,
                origin=self.origin,
                canon=self.canon,
                master=self.master,
                develop=self.develop,
                release=self.release,
                hotfix=self.hotfix,
                repo=self._repo,
                gh=self._gh,
                offline=self.offline,
            )

            self.hotfix_manager = HotfixManager(
                debug=self.DEBUG,
                prefix=self._cr.flowhub.prefix.hotfix,
                origin=self.origin,
                canon=self.canon,
                master=self.master,
                develop=self.develop,
                release=self.release,
                hotfix=self.hotfix,
                repo=self._repo,
                gh=self._gh,
                offline=self.offline,
            )

            self.pull_manager = PullRequestManager(
                debug=self.DEBUG,
                prefix=self._cr.flowhub.structure.name,
                origin=self.origin,
                canon=self.canon,
                master=self.master,
                develop=self.develop,
                release=self.release,
                hotfix=self.hotfix,
                repo=self._repo,
                gh=self._gh,
                offline=self.offline,
            )

    def do_auth(self):
        """Generates the authorization to do things with github."""
        try:
            token = self._cr.flowhub.auth.token
            self._gh = Github(token)
            if self.DEBUG > 0:
                print "GitHub Engine authorized by token in settings."
        except AttributeError:
            print (
                "Flowhub needs permission to access your GitHub repositories.\n"
                "Entering your credentials now will grant Flowhub the access it "
                "requires."
            )
            if not self._create_token():
                return False
            # Refresh the readers
            self._cr = Configurator(self._repo.config_reader())

        return True

    def _create_token(self):
        # Don't store the users' information.
        for i in range(3):
            self._gh = Github(raw_input("Username: "), getpass.getpass())

            try:
                auth = self._gh.get_user().create_authorization(
                    ['user', 'repo', 'gist'],
                    'Flowhub Client',
                )
                break
            except GithubException:
                print "Invalid username/password combination."
                if i == 2:
                    return False

        token = auth.token
        if self.DEBUG > 2:
            print "Token generated: ", token
        # set the token globally, rather than on the repo level.
        authing = subprocess.check_output(
            'git config --global --add flowhub.auth.token {}'.format(token),
            shell=True,
        ).strip()
        if self.DEBUG > 2:
            print "result of config set:", authing

        return True

    def setup_repository_structure(
        self,
        name,
        origin,
        canon,
        master,
        develop,
        feature,
        release,
        hotfix,
    ):
        cw = self._repo.config_writer()
        if self.DEBUG > 2:
            print "Begin repo setup"
        if not cw.has_section('flowhub "structure"'):
            cw.add_section('flowhub "structure"')

        cw.set('flowhub "structure"', 'name', name)

        cw.set('flowhub "structure"', 'origin', origin)
        cw.set('flowhub "structure"', 'canon', canon)

        cw.set('flowhub "structure"', 'master', master)

        if not self._branch_exists(master):
            print "\tCreating branch {}".format(master)
            self._repo.create_head(master)

        cw.set('flowhub "structure"', 'develop', develop)
        if not self._branch_exists(develop):
            print "\tCreating branch {}".format(develop)
            self._repo.create_head(develop)

        if not cw.has_section('flowhub "prefix"'):
            cw.add_section('flowhub "prefix"')

        cw.set('flowhub "prefix"', 'feature', feature)
        cw.set('flowhub "prefix"', 'release', release)
        cw.set('flowhub "prefix"', 'hotfix', hotfix)
        cw.write()

        # Refresh the read-only reader.
        self._cr = Configurator(self._repo.config_reader())

    def _branch_exists(self, branch_name):
        if self.DEBUG > 2:
            print "Checking for existence of branch {}".format(branch_name)
        return getattr(self._repo.heads, branch_name, None) is not None

    def _remote_exists(self, repo_name):
        if self.DEBUG > 2:
            print "Checking for existence of remote {}".format(repo_name)
        return getattr(self._repo.remotes, repo_name, None) is not None

    def __get_branch_by_name(self, name):
        try:
            return getattr(self._repo.heads, name)
        except AttributeError:
            raise NoSuchBranch(name)

    @property
    def develop(self):
        develop_name = self._cr.flowhub.structure.develop
        if self.DEBUG > 3:
            print "finding develop branch {}".format(develop_name)
        return self.__get_branch_by_name(develop_name)

    @property
    def master(self):
        master_name = self._cr.flowhub.structure.master
        if self.DEBUG > 3:
            print "finding master branch {}".format(master_name)
        return self.__get_branch_by_name(master_name)

    def __get_remote_by_name(self, name):
        try:
            return getattr(self._repo.remotes, name)
        except AttributeError:
            raise NoSuchRemote(name)

    @property
    def origin(self):
        origin_name = self._cr.flowhub.structure.origin
        if self.DEBUG > 3:
            print "finding origin repo {}".format(origin_name)
        return self.__get_remote_by_name(origin_name)

    @property
    def canon(self):
        canon_name = self._cr.flowhub.structure.canon
        if self.DEBUG > 3:
            print "finding canon repo {}".format(canon_name)
        return self.__get_remote_by_name(canon_name)

    @property
    def gh_canon(self):
        # if this isn't a fork, we have slightly different sha's.
        if self.canon == self.origin:
            gh_parent = self._gh_repo
        else:
            gh_parent = self._gh_repo.parent

        return gh_parent

    @property
    def release(self):
        # official version releases are named release/#.#.#
        releases = [x for x in self._repo.branches if x.name.startswith(
            self._cr.flowhub.prefix.release,
        )]

        if releases:
            return releases[0]
        else:
            return None

    @property
    def hotfix(self):
        # official version hotfixes are named release/#.#.#
        hotfixes = [x for x in self._repo.branches if x.name.startswith(
            self._cr.flowhub.prefix.hotfix,
        )]

        if hotfixes:
            return hotfixes[0]
        else:
            return None

    def _create_pull_request(self, base, head, summary):

        # try to glean issue numbers from branch
        pr_from_issue = self.pull_manager.create_from_branch_name(base, head, summary)
        if pr_from_issue:
            return pr_from_issue

        is_issue = raw_input("is this feature answering an issue? [y/N] ").lower() == 'y'
        if not is_issue:
            issue = self._open_issue(summary=summary, return_issue=True)

            if self.DEBUG > 1:
                print (issue.title, issue.body, base, head)

        else:
            good_number = False
            while not good_number:
                try:
                    issue_number = int(raw_input("issue number: "))
                except ValueError:
                    print "not a valid number"
                    continue

                issue = self.pull_manager.get_issue(issue_number)
                if issue is None:
                    print "no such issue"
                    continue

                good_number = True

        pr = self.pull_manager.create_pull(
            issue=issue,
            base=base,
            head=head,
            summary=summary,
        )

        return pr

    def _create_feature(self, name=None, with_tracking=True, summary=None):
        if name is None:
            print "please provide a feature name."
            return False

        if summary is None:
            summary = []

        branch = self.feature_manager.start(
            name,
            with_tracking,
            summary,
        )

        branch.checkout()

        summary += [
            "Checked out branch {}".format(branch.name),
        ]

        return True
    create_feature = with_summary(_create_feature)

    def work_feature(self, name=None):
        """Simply checks out the feature branch for the named feature."""
        if name is None:
            print "please provide a feature name."
            return False

        branches = self.feature_manager.fuzzy_get(name)

        if len(branches) == 1:
            branches[0].checkout()
            print "switched to branch '{}'".format(branches[0].name)

        elif len(branches) > 1:
            print "multiple branches found:"
            for branch in branches:
                print "\t{}".format(branch)

        else:
            print "No feature starts with {}".format(name)

        return True

    def _accept_feature(self, name=None, delete_feature_branch=True, summary=None):
        if summary is None:
            summary = []

        return_branch = self._repo.head.reference
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.feature not in name:
                print (
                    "Please provide a feature name, or switch to "
                    "the feature branch you want to mark as accepted."
                )
                return False

            name = name.replace(self._cr.flowhub.prefix.feature, '')
            return_branch = self.develop

        self.feature_manager.accept(
            name,
            summary=summary,
            with_delete=delete_feature_branch,
        )

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]

        return True
    accept_feature = with_summary(_accept_feature)

    def _abandon_feature(self, name=None, summary=None):
        if summary is None:
            summary = []
        return_branch = self._repo.head.reference
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.feature not in name:
                print (
                    "Please provide a feature name, or switch to "
                    "the feature branch you want to abandon."
                )
                return False

            name = name.replace(self._cr.flowhub.prefix.feature, '')
            return_branch = self.develop

        if self.DEBUG > 0:
            print "Abandoning feature branch..."

        # checkout develop
        # branch -D feature_prefix+name
        # push --delete origin feature_prefix+name

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(
                return_branch.name,
            ),
        ]

        self.feature_manager.abandon(
            name,
            summary=summary,
        )
        return True
    abandon_feature = with_summary(_abandon_feature)

    @online_only
    def _publish_feature(self, name=None, summary=None):
        if summary is None:
            summary = []
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.feature not in name:
                print (
                    "please provide a feature name, or switch to "
                    "the feature branch you want to publish."
                )
                return False

            name = name.replace(self._cr.flowhub.prefix.feature, '')

        branch = self.feature_manager.publish(name, summary)

        # we don't have access to gh_canon if we're offline
        if not self.offline:
            base = self.develop
            pr = self.pull_manager.add_to_pull(base, branch, summary)

            if not pr:
                pr = self._create_pull_request(base, branch, summary)

        return True
    publish_feature = with_summary(_publish_feature)

    def list_features(self):
        features = [
            b for b in self._repo.branches
            if b.name.startswith(self._cr.flowhub.prefix.feature)
        ]
        if not features:
            print "There are no feature branches."
            return

        for branch in features:
            display = '{}'.format(
                branch.name.replace(
                    self._cr.flowhub.prefix.feature,
                    ''
                ),
            )
            if self._repo.head.reference.name == branch.name:
                display = '* {}'.format(display)
            else:
                display = '  {}'.format(display)

            print display

        return features

    def _start_release(self, name=None, summary=None):
        # checkout develop
        # if already release branch, abort.
        # checkout -b relase_prefix+branch_name

        if summary is None:
            summary = []

        if name is None:
            print "Please provide a release name."
            return False

        if any([
            x for x in self._repo.branches
                if x.name.startswith(self._cr.flowhub.prefix.release)
        ]):
            print "You already have a release in the works - please finish that one."
            return False

        if self.DEBUG > 0:
            print "Creating new release branch..."

        branch = self.release_manager.start(name, summary)

        branch.checkout()

        summary += [
            "Checked out branch {}"
            "\n\nBump the release version now!".format(branch)
        ]

        return True
    start_release = with_summary(_start_release)

    @with_summary
    def stage_release(self, summary=None):
        summary += [
            "Release branch sent off to stage",
        ]
        summary += [
            "Release branch checked out and refreshed on stage."
            "\n\nLOL just kidding, this doesn't do anything."
        ]

    def _publish_release(
        self,
        name=None,
        with_delete=True,
        summary=None,
        tag_info=None,
    ):
        # fetch canon
        # checkout master
        # merge canon master
        # merge --no-ff name
        # tag
        # checkout develop
        # merge canon develop
        # merge --no-ff name
        # push --tags canon
        # delete release branch
        # git push origin --delete name
        return_branch = self._repo.head.reference

        if summary is None:
            summary = []

        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.release not in name:
                print (
                    "Please provide a release name, or switch to "
                    "the release branch you want to publish."
                )
                return False

            name = name.replace(self._cr.flowhub.prefix.release, '')
            return_branch = self.develop

        self.release_manager.publish(name, with_delete, tag_info, summary)

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]
        return name
    publish_release = with_summary(_publish_release)

    @online_only
    def _contribute_release(self, summary=None):
        if summary is None:
            summary = []

        if not (self.release and self.release.commit in self._repo.head.reference.object.iter_parents()):
            # Don't allow random branches to be contributed.
            print (
                "You are attempting to contribute a branch that is not a "
                "descendant of a current release.\n"
                "Unfortunately, this isn't allowed."
            )
            return False

        branch = self._repo.head.reference

        self.release_manager.contribute(branch, summary)

        pr = self.pull_manager.add_to_pull(self.release, branch, summary)
        if not pr:
            pr = self._create_pull_request(self.release, branch, summary)

        return True
    contribute_release = with_summary(_contribute_release)

    @with_summary
    def cleanup_branches(self, summary=None, targets=""):
        current_branch = self._repo.head.reference
        hotfix_prefix = self._cr.flowhub.prefix.hotfix
        release_prefix = self._cr.flowhub.prefix.release

        for branch in self._repo.branches:
            if (
                ('u' in targets and branch.name.startswith(self._cr.flowhub.prefix.feature))
                or ('r' in targets and branch.name.startswith(self._cr.flowhub.prefix.release))
                or ('t' in targets and branch.name.startswith(self._cr.flowhub.prefix.hotfix))
            ):
                # Feature branches get removed if they're fully merged in to something else.
                # NOTE: this will delete branch references that have no commits in them.
                if branch == current_branch:
                    print (
                        "Currently checked out branch would be cleaned up; skipping."
                        "If you want this branch to be cleaned up, switch to a different branch"
                        "and re-run this command."
                    )
                    continue

                try:
                    remote_branch = branch.tracking_branch()

                    # If it failed because it's an un-recognizably-merged hotfix
                    # or release contribution, but there's no hotfix/release branch
                    # currently, delete it.
                    if hotfix_prefix in branch.name and not self.hotfix:
                        self._repo.delete_head(branch.name, force=True)
                    elif release_prefix in branch.name and not self.release:
                        self._repo.delete_head(branch.name, force=True)
                    else:
                        self._repo.delete_head(branch.name)
                    summary += [
                        "Deleted local branch {}".format(branch.name)
                    ]

                    if remote_branch:
                        # get rid of the 'origin/' part of the remote name
                        remote_name = '/'.join(remote_branch.name.split('/')[1:])
                        self.origin.push(
                            remote_name,
                            delete=True,
                        )
                        summary[-1] += ' and remote branch {}'.format(remote_branch.name)
                    else:
                        # Sometimes the tracking isn't set properly (at least for empty featuers?)
                        # so, we brute it here.
                        if hasattr(self.origin.refs, branch.name):
                            self.origin.push(
                                branch.name,
                                delete=True,
                            )
                            summary[-1] += '\n\tand remote branch {}/{}'.format(
                                self.origin.name,
                                branch.name,
                            )

                except git.GitCommandError as e:
                    print e
                    continue

    def _start_hotfix(self, name=None, issues=None, summary=None):
        # Checkout master
        # if already hotfix branch, abort.
        # checkout -b hotfix_prefix+branch_name
        if summary is None:
            summary = []

        if name is None:
            print "Please provide a release name."
            return

        if any([
            x for x in self._repo.branches
                if x.name.startswith(self._cr.flowhub.prefix.hotfix)
        ]):
            print (
                "You already have a hotfix in the works - please finish that one."
            )
            return False

        if self.DEBUG > 0:
            print "Creating new hotfix branch..."

        # checkout develop
        # checkout -b hotfix/name

        branch = self.hotfix_manager.start(name, issues, summary)

        # Checkout the branch.
        branch.checkout()
        summary += [
            "Checked out branch {}"
            "\n\nBump the release version now!".format(branch),
        ]
        return True

    start_hotfix = with_summary(_start_hotfix)

    def _publish_hotfix(
        self,
        name=None,
        summary=None,
        with_delete=True,
        tag_info=None,
    ):
        # fetch canon
        # checkout master
        # merge --no-ff hotfix
        # tag
        # checkout develop
        # merge --no-ff hotfix
        # push --tags canon
        # delete hotfix branches
        return_branch = self._repo.head.reference

        if summary is None:
            summary = []
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a hotfix branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.hotfix not in name:
                print ("please provide a hotfix name, or switch to the hotfix branch you want to publish.")
                return

            name = name.replace(self._cr.flowhub.prefix.hotfix, '')
            return_branch = self.develop

        self.hotfix_manager.publish(name, tag_info, with_delete, summary)

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]

        return name
    publish_hotfix = with_summary(_publish_hotfix)

    @online_only
    def _contribute_hotfix(self, summary=None):
        if not (self.hotfix and self.hotfix.commit in self._repo.head.reference.object.iter_parents()):
            # Don't allow random branches to be contributed.
            print (
                "You are attempting to contribute a branch that is not a "
                "descendant of the current hotfix.\n"
                "Unfortunately, this isn't allowed."
            )
            return False

        branch = self._repo.head.reference

        self.release_manager.contribute(branch, summary)
        pr = self.pull_manager.add_to_pull(self.hotfix, branch, summary)

        if not pr:
            self._create_pull_request(self.hotfix, branch, summary)

        return True
    contribute_release = with_summary(_contribute_release)

    @online_only
    def _open_issue(
        self,
        title=None,
        labels=None,
        create_branch=False,
        summary=None,
        return_issue=False
    ):
        if title is None:
            title = raw_input("Title for this issue: ")
        else:
            print "Title for this issue: ", title

        if labels is None:
            labels = []

        if summary is None:
            summary = []

        # Open the $EDITOR, if you can...
        descr_f = tempfile.NamedTemporaryFile(delete=False)
        descr_f.file.write(
            "\n\n# Write your description above. Remember - you can use GitHub markdown syntax!"
        )
        if self.DEBUG > 3:
            print "Temp file: ", descr_f.name
        # regardless, close the tempfile.
        descr_f.close()

        try:
            editor_result = subprocess.check_call(
                "$EDITOR {}".format(descr_f.name),
                shell=True
            )
        except OSError:
            if self.DEBUG > 2:
                print "Hmm...are you on Windows?"
            editor_result = 126

        if self.DEBUG > 3:
            print "result of $EDITOR: ", editor_result

        if editor_result == 0:
            # Re-open the file to get new contents...
            fnew = open(descr_f.name, 'r')
            # and remove the first line
            body = fnew.readlines()
            if body[-1].startswith('# Write your description'):
                body = body[:-1]

            body = "".join(body)

            fnew.close()
        else:
            body = raw_input(
                "Description (remember, you can use GitHub markdown):\n"
            )

        if self.DEBUG > 3:
            print "Description used:\n", body

        issue = self.pull_manager.open_issue(title, body, labels, summary)

        if create_branch:
            feature_name = "{}-{}".format(
                issue.number,
                title.replace(' ', '-').lower(),
            )
            self.feature_manager.start(feature_name, summary, with_tracking=False)

        if return_issue:
            return issue

    open_issue = with_summary(_open_issue)
