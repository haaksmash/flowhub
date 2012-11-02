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


class Engine(object):
    def __init__(self, debug=0, skip_auth=False):
        self.__debug = debug
        if self.__debug > 2:
            print "initing engine"

        self._repo = self._get_repo()
        if not self._repo:
            return

        self._cw = Configurator(self._repo.config_writer())
        self._cr = Configurator(self._repo.config_reader())

        self._gh = None

        if not skip_auth:
            if self.__debug > 0:
                print "Authorizing engine..."
            if not self.do_auth():
                print "Authorization failed! Exiting."
                return

            try:
                self._gh_repo = self._gh.get_user().get_repo(self._cr.flowhub.structure.name)
            except GithubException:
                try:
                    self._get_repo = [x for x in self._gh.get_user().get_repos() if x.name == self._cr.flowhub.structure.name][0]
                except IndexError:
                    raise ImproperlyConfigured("No repo with given name: {}".format(self._cr.flowhub.structure.name))

            if self._gh.rate_limiting[0] < 100:
                warnings.warn("You are close to exceeding your GitHub access "
                    "rate; {} left out of {} initially".format(*self._gh.rate_limiting))
        else:
            if self.__debug > 0:
                print "Skipping auth - GitHub accesses will fail."

    def do_auth(self):
        """Generates the authorization to do things with github."""
        try:
            token = self._cr.flowhub.auth.token
            self._gh = Github(token)
            if self.__debug > 0:
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

        if self.__debug > 2:
            print "Checking for repo setup"
        if not hasattr(self._cr.flowhub, 'structure') or not hasattr(self._cr.flowhub.structure, 'name'):
            print (
                "This repository is not yet Flowhub-enabled. Let's take care of that now."
            )
            self.setup_repository_structure()
            print '\n'.join((
                "You can change these settings just like all git settings, using the\n",
                "\tgit config\n",
                "command."
            ))
        return True

    def _create_token(self):
        # Don't store the users' information.
        for i in range(3):
            self._gh = Github(raw_input("Username: "), getpass.getpass())

            try:
                auth = self._gh.get_user().create_authorization(
                    'user,repo,gist',
                    'Flowhub Client',
                )
                break
            except GithubException:
                print "Invalid username/password combination."
                if i == 2:
                    return False

        token = auth.token
        if self.__debug > 2:
            print "Token generated: ", token
        # set the token globally, rather than on the repo level.
        authing = subprocess.check_output('git config --global --add flowhub.auth.token {}'.format(token), shell=True).strip()
        if self.__debug > 2:
            print "result of config set:", authing

        return True

    def setup_repository_structure(self):
        if self.__debug > 2:
            print "Begin repo setup"
        if not hasattr(self._cw, 'flowhub') or not hasattr(self._cw.flowhub, 'structure'):
            self._cw.add_section('flowhub "structure"')

        self._cw.flowhub.structure.name = raw_input("Name of the GitHub repository for this flowhub: ")

        self._cw.flowhub.structure.origin = raw_input("Name of your github remote [origin]: ") or 'origin'
        if not self._ensure_remote_exists(self._cw.flowhub.structure.origin):
            print "Whoops! That remote doesn't exist."
            remote_url = raw_input("Remote url: ")
            self._repo.create_remote(
                self._cw.flowhub.structure.origin,
                remote_url,
            )
        self._cw.flowhub.structure.canon = raw_input('Name of the organization remote [canon]: ') or 'canon'
        if not self._ensure_remote_exists(self._cw.flowhub.structure.canon):
            print "Whoops! That remote doesn't exist."
            remote_url = raw_input("Remote url: ")
            self._repo.create_remote(
                self._cw.flowhub.structure.canon,
                remote_url,
            )

        self._cw.flowhub.structure.master = raw_input("Name of the stable branch [master]: ") or 'master'
        if not self._ensure_branch_exists(self._cw.flowhub.structure.master):
            print "\tCreating branch {}".format(self._cw.flowhub.structure.master)
            self._repo.create_head(self._cw.flowhub.structure.master)

        self._cw.flowhub.structure.develop = raw_input("Name of the development branch [develop]: ") or 'develop'
        if not self._ensure_branch_exists(self._cw.flowhub.structure.master):
            print "\tCreating branch {}".format(self._cw.flowhub.structure.develop)
            self._repo.create_head(self._cw.flowhub.structure.master)

        if not hasattr(self._cr.flowhub, 'prefix'):
            self._cw.add_section('flowhub "prefix"')

        self._cw.flowhub.prefix.feature = raw_input("Prefix for feature branches [feature/]: ") or 'feature/'
        self._cw.flowhub.prefix.release = raw_input("Prefix for release branches [release/]: ") or "release/"
        self._cw.flowhub.prefix.hotfix = raw_input("Prefix for hotfix branches [hotfix/]: ") or "hotfix/"

        # Refresh the read-only reader.
        self._cr = Configurator(self._repo.config_reader())

    def _ensure_branch_exists(self, branch_name):
        if self.__debug > 2:
            print "Checking for existence of branch {}".format(branch_name)
        return getattr(self._repo.heads, branch_name, None) is not None

    def _ensure_remote_exists(self, repo_name):
        if self.__debug > 2:
            print "Checking for existence of remote {}".format(repo_name)
        return getattr(self._repo.remotes, repo_name, None) is not None

    @property
    def develop(self):
        if self.__debug > 3:
            print "finding develop branch {}".format(self._cr.flowhub.structure.develop)
        return [x for x in self._repo.heads if x.name == self._cr.flowhub.structure.develop][0]

    @property
    def master(self):
        if self.__debug > 3:
            print "finding master branch {}".format(self._cr.flowhub.structure.master)
        return [x for x in self._repo.heads if x.name == self._cr.flowhub.structure.master][0]

    @property
    def origin(self):
        if self.__debug > 3:
            print "finding origin repo {}".format(self._cr.flowhub.structure.origin)
        return self._repo.remote(self._cr.flowhub.structure.origin)

    @property
    def canon(self):
        if self.__debug > 3:
            print "finding canon repo {}".format(self._cr.flowhub.structure.canon)
        return self._repo.remote(self._cr.flowhub.structure.canon)

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
            ) and re.match('\d.\d.\d', x.name.split('/')[-1])]

        if hotfixes:
            return hotfixes[0]
        else:
            return None

    def _get_repo(self):
        """Get the repository of this directory, or error out if not found"""
        if self.__debug > 2:
            print "checking for repo-ness"
        try:
            repo_dir = subprocess.check_output("git rev-parse --show-toplevel", shell=True).strip()
        except subprocess.CalledProcessError:
            print "You don't appear to be in a git repository."
            return False

        if self.__debug > 2:
            print "repo directory: ", repo_dir

        if self.__debug > 2:
            print "creating Repo object from dir:", repo_dir
        repo = git.Repo(repo_dir)

        return repo

    def _create_pull_request(self, base, head, repo=None):
        if repo is None:
            repo = self.gh_canon

        if self.__debug > 1:
            print "setting up new pull-request"

        component_name = head.split('/')[-1]
        match = re.match('^\d+', component_name)
        if match:
            issue_number = match.group()
            issue = repo.get_issue(int(issue_number))
            pr = repo.create_pull(
                issue=issue,
                base=base,
                head=head,
            )
            return pr

        is_issue = raw_input("Is this feature answering an issue? [y/N] ").lower() == 'y'

        if not is_issue:
            issue = self._open_issue(return_values=True)

            if self.__debug > 1:
                print (issue.title, issue.body, base, head)

        else:
            good_number = False
            while not good_number:
                try:
                    issue_number = int(raw_input("Issue number: "))
                except ValueError:
                    print "That isn't a valid number."
                    continue

                try:
                    issue = repo.get_issue(issue_number)
                except GithubException:
                    print "That's not a valid issue."
                    continue

                good_number = True

            pr = repo.create_pull(
                issue=issue,
                base=base,
                head=head,
            )

        return pr

    def _create_feature(self, name=None, create_tracking_branch=True, summary=None):
        if name is None:
            print "Please provide a feature name."
            return

        if self.__debug > 0:
            print "Creating new feature branch..."
        # Checkout develop
        # checkout -b feature_prefix+branch_name
        # push -u origin feature_prefix+branch_name

        branch_name = "{}{}".format(
            self._cr.flowhub.prefix.feature,
            name
        )
        self._repo.create_head(
            branch_name,
            commit=self.develop,  # Requires a develop branch.
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self._cr.flowhub.structure.develop,
            )
        ]

        if create_tracking_branch:
            if self.__debug > 0:
                print "Adding a tracking branch to your GitHub repo"
            self._repo.git.push(
                self._cr.flowhub.structure.origin,
                branch_name,
                set_upstream=True
            )
            summary += [
                "Created a remote tracking branch on {} for {}".format(
                    self.origin.name,
                    branch_name,
                ),
            ]

        branch = [x for x in self._repo.branches if x.name == branch_name][0]

        # Checkout the branch.
        branch.checkout()
        summary += [
            "Checked out branch {}".format(branch_name),
        ]

    def work_feature(self, name=None, issue=None):
        """Simply checks out the feature branch for the named feature."""
        if name is None and issue is None:
            print "please provide a feature name or an issue number."
            return

        if self.__debug > 0:
            print "switching to a feature branch..."

        if name is not None:
            branch_name = "{}{}".format(
                self._cr.flowhub.prefix.feature,
                name
            )

        elif issue is not None:
            branch_name = None
            for branch in self._repo.branches:
                if not branch.name.startswith(self._cr.flowhub.prefix.feature):
                    continue

                fname = branch.name[len(self._cr.flowhub.prefix.feature):]
                if fname.startswith(str(issue)):
                    branch_name = branch.name
                    break

        branches = [x for x in self._repo.branches if x.name == branch_name]
        if branches:
            branch = branches[0]

            branch.checkout()
            print "Switched to branch '{}'".format(branch.name)

        else:
            print "No feature with name {}".format(name)
            return

    create_feature = with_summary(_create_feature)

    @with_summary
    def accept_feature(self, name=None, summary=None):
        return_branch = self._repo.head.reference
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.feature not in name:
                print ("Please provide a feature name, or switch to "
                    "the feature branch you want to mark as accepted.")
                return

            name = name.replace(self._cr.flowhub.prefix.feature, '')
            return_branch = self.develop

        self.canon.fetch()
        summary += [
            "Latest objects fetched from {}".format(self.canon.name),
        ]
        self.develop.checkout()
        self._repo.git.merge(
            "{}/{}".format(self.canon.name, self.develop.name),
        )
        summary += [
            "Updated {}".format(self.develop.name),
        ]

        branch_name = "{}{}".format(
            self._cr.flowhub.prefix.feature,
            name,
        )

        self._repo.delete_head(
            branch_name,
        )
        summary += [
            "Deleted {} from local repository".format(branch_name),
        ]
        self.origin.push(
            branch_name,
            delete=True,
        )
        summary += [
            "Deleted {} from {}".format(branch_name, self.origin.name),
        ]

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]

    @with_summary
    def abandon_feature(self, name=None, summary=None):
        return_branch = self._repo.head.reference
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.feature not in name:
                print ("Please provide a feature name, or switch to "
                    "the feature branch you want to abandon.")
                return

            name = name.replace(self._cr.flowhub.prefix.feature, '')
            return_branch = self.develop

        if self.__debug > 0:
            print "Abandoning feature branch..."

        # checkout develop
        # branch -D feature_prefix+name
        # push --delete origin feature_prefix+name

        return_branch.checkout()

        branch_name = "{}{}".format(
            self._cr.flowhub.prefix.feature,
            name,
        )

        self._repo.delete_head(
            branch_name,
            force=True,
        )
        summary += [
            "Deleted branch {} locally and from remote {}".format(
                branch_name,
                self._cr.flowhub.structure.origin,
            ),
        ]

        self._repo.git.push(
            self._cr.flowhub.structure.origin,
            branch_name,
            delete=True,
            force=True,
        )
        summary += [
            "Checked out branch {}".format(
                return_branch.name,
            ),
        ]

    @with_summary
    def publish_feature(self, name, summary=None):
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.feature not in name:
                print ("please provide a feature name, or switch to "
                    "the feature branch you want to publish.")
                return

            name = name.replace(self._cr.flowhub.prefix.feature, '')

        branch_name = "{}{}".format(
            self._cr.flowhub.prefix.feature,
            name,
        )
        self._repo.git.push(
                self._cr.flowhub.structure.origin,
                branch_name,
                set_upstream=True,
        )
        summary += [
            "Updated {}/{}".format(self.origin.name, branch_name)
        ]

        base = self.develop.name
        if self.gh_canon == self.origin:
            head = branch_name
        else:
            head = "{}:{}".format(self._gh.get_user().login, branch_name)

        prs = [x for x in self.gh_canon.get_pulls('open') if x.head.label == head \
                    or x.head.label == "{}:{}".format(self._gh.get_user().login, head)]
        if prs:
            # If there's already a pull-request, don't bother hitting the gh api.
            summary += [
                "New commits added to existing pull-request"
                "\n\turl: {}".format(prs[0].issue_url)
            ]
            return

        pr = self._create_pull_request(base, head)
        summary += [
            "New pull request created: {} into {}"
            "\n\turl: {}".format(
                head,
                base,
                pr.issue_url,
            )
        ]

    def list_features(self):
        features = [b for b in self._repo.branches if b.name.startswith(self._cr.flowhub.prefix.feature)]
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

    @with_summary
    def start_release(self, name, summary=None):
        # checkout develop
        # if already release branch, abort.
        # checkout -b relase_prefix+branch_name
        if name is None:
            print "Please provide a release name."
            return

        if any([x for x in self._repo.branches if x.name.startswith(self._cr.flowhub.prefix.release)]):
            print "You already have a release in the works - please finish that one."
            return

        if self.__debug > 0:
            print "Creating new release branch..."

        # checkout develop
        # checkout -b release/name

        branch_name = "{}{}".format(
            self._cr.flowhub.prefix.release,
            name,
        )
        self._repo.create_head(
            branch_name,
            commit=self.develop,
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self._cr.flowhub.structure.develop,
            ),
        ]

        if self.__debug > 0:
            print "Adding a tracking branch to your GitHub repo"
        self.canon.push(
            "{0}:{0}".format(branch_name),
            set_upstream=True,
        )
        summary += [
            "Pushed {} to {}".format(branch_name, self.canon.name),
        ]

        branch = [x for x in self._repo.branches if x.name == branch_name][0]

        # Checkout the branch.
        branch.checkout()
        summary += [
            "Checked out branch {}"
            "\n\nBump the release version now!".format(branch_name)
        ]

    @with_summary
    def stage_release(self, summary=None):
        summary += [
            "Release branch sent off to stage",
        ]
        summary += [
            "Release branch checked out and refreshed on stage."
            "\n\nLOL just kidding, this doesn't do anything."
        ]

    @with_summary
    def publish_release(self, name=None, delete_release_branch=True, summary=None):
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
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.release not in name:
                print ("please provide a release name, or switch to "
                    "the release branch you want to publish.")
                return

            name = name.replace(self._cr.flowhub.prefix.release, '')
            return_branch = self.develop

        release_name = "{}{}".format(
            self._cr.flowhub.prefix.release,
            name,
        )

        self.canon.fetch()
        summary += [
            "Latest objects fetched from {}".format(self.canon.name),
        ]

        # TODO: ensure equality of remote and local master/develop branches
        # TODO: handle merge conflicts.
        # merge into master
        self.master.checkout()
        self._repo.git.merge(
            release_name,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(release_name, self.master.name),
        ]

        # and tag
        tag_message = raw_input("Message for this tag ({}): ".format(name))
        self._repo.create_tag(
            path=name,
            ref=self.master,
            message=tag_message,
        )
        summary += [
            "New tag ({}:{}) created at {}'s tip".format(name, tag_message, self.master.name),
        ]

        # merge into develop
        self.develop.checkout()
        self._repo.git.merge(
            release_name,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(release_name, self.develop.name),
        ]

        # push to canon
        self.canon.push()
        self.canon.push(tags=True)
        summary += [
            "{}, {}, and tags have been pushed to {}".format(self.master.name, self.develop.name, self.canon.name),
        ]

        if delete_release_branch:
            self._repo.delete_head(release_name)
            self.canon.push(
                release_name,
                delete=True,
            )
            summary += [
                "Branch {} {}".format(release_name, 'removed' if delete_release_branch else "still available"),
            ]

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]

    @with_summary
    def contribute_release(self, summary=None):
        if not (self.release and self.release.commit in self._repo.head.reference.object.iter_parents()):
            # Don't allow random branches to be contributed.
            print (
                "You are attempting to contribute a branch that is not a "
                "descendant of a current release.\n"
                "Unfortunately, this isn't allowed."
            )
            return

        branch_name = self._repo.head.reference.name
        self._repo.git.push(
                self._cr.flowhub.structure.origin,
                branch_name,
                set_upstream=True,
        )

        base = self.release.name
        if self.gh_canon == self.origin:
            head = branch_name
        else:
            head = "{}:{}".format(self._gh.get_user().login, branch_name)

        prs = [x for x in self.gh_canon.get_pulls('open') if x.head.label == head \
                    or x.head.label == "{}:{}".format(self._gh.get_user().login, head)]
        if prs:
            # If there's already a pull-request, don't bother hitting the gh api.
            summary += [
                "New commits added to existing pull-request"
                "\n\turl: {}".format(prs[0].issue_url)
            ]
            return

        pr = self._create_pull_request(base, head)
        summary += [
            "New pull request created: {} into {}"
            "\n\turl: {}".format(
                head,
                base,
                pr.issue_url,
            )
        ]

    @with_summary
    def cleanup_branches(self, summary=None, targets=""):
        current_branch = self._repo.head.reference
        hotfix_prefix = self._cr.flowhub.prefix.hotfix
        release_prefix = self._cr.flowhub.prefix.release

        for branch in self._repo.branches:
            if ('u' in targets and branch.name.startswith(self._cr.flowhub.prefix.feature))\
                or ('r' in targets and branch.name.startswith(self._cr.flowhub.prefix.release))\
                or ('t' in targets and branch.name.startswith(self._cr.flowhub.prefix.hotfix)):
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

    @with_summary
    def start_hotfix(self, name, issues=None, summary=None):
        # Checkout master
        # if already hotfix branch, abort.
        # checkout -b hotfix_prefix+branch_name
        if name is None:
            print "Please provide a release name."
            return

        if any([x for x in self._repo.branches if x.name.startswith(self._cr.flowhub.prefix.hotfix)]):
            print (
                "You already have a hotfix in the works - please finish that one."
            )

        if self.__debug > 0:
            print "Creating new hotfix branch..."

        # checkout develop
        # checkout -b release/name

        branch_name = "{}{}{}".format(
            self._cr.flowhub.prefix.hotfix,
            "-".join(['{}'.format(issue) for issue in issues]) + '-' if issues is not None else "",
            name,
        )
        self.canon.fetch()
        summary += [
            "Latest objects fetched from {}".format(self.canon.name),
        ]
        self.master.checkout()
        self._repo.git.merge(
            "{}/{}".format(self.canon.name, self.master.name),
        )
        summary += [
            "Updated {}".format(self.master.name),
        ]

        self._repo.create_head(
            branch_name,
            commit=self.master,
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self.master.name,
            ),
        ]

        if self.__debug > 0:
            print "Adding a tracking branch to your GitHub repo"
        self.canon.push(
            "{0}:{0}".format(branch_name),
            set_upstream=True,
        )
        summary += [
            "Pushed {} to {}".format(branch_name, self.canon.name),
        ]

        # simulate self._repo.branches.branch_name, which is what we really want
        branch = getattr(self._repo.branches, branch_name)

        # Checkout the branch.
        branch.checkout()
        summary += [
            "Checked out branch {}"
            "\n\nBump the release version now!".format(branch_name),
        ]

    @with_summary
    def publish_hotfix(self, name, summary=None, delete_hotfix_branch=True):
        # fetch canon
        # checkout master
        # merge --no-ff hotfix
        # tag
        # checkout develop
        # merge --no-ff hotfix
        # push --tags canon
        # delete hotfix branches
        return_branch = self._repo.head.reference
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a hotfix branch.
            name = self._repo.head.reference.name
            if self._cr.flowhub.prefix.hotfix not in name:
                print ("please provide a hotfix name, or switch to "
                    "the hotfix branch you want to publish.")
                return

            name = name.replace(self._cr.flowhub.prefix.hotfix, '')
            return_branch = self.develop

        hotfix_name = "{}{}".format(
            self._cr.flowhub.prefix.hotfix,
            name,
        )

        self.canon.fetch()
        summary += [
            "Latest objects fetched from {}".format(self.canon.name),
        ]

        # TODO: ensure equality of remote and local master/develop branches
        # TODO: handle merge conflicts.
        # merge into master
        self.master.checkout()
        self._repo.git.merge(
            hotfix_name,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(hotfix_name, self.master.name),
        ]

        # and tag
        issue_numbers = re.findall('(\d+)-', name)
        # cut off any issue numbers that may be there
        default_tag = name[len('-'.join(issue_numbers)) + 1:] if issue_numbers else name
        tag_label = raw_input("Tag Label [{}]: ".format(default_tag)) or default_tag
        tag_message = raw_input("Message for this tag: ")
        self._repo.create_tag(
            path=tag_label,
            ref=self.master,
            message=tag_message,
        )
        summary += [
            "New tag ({}:{}) created at {}'s tip".format(name, tag_message, self.master.name),
        ]

        # merge into develop (or release, if exists)
        if self.release:
            trunk = self.release
        else:
            trunk = self.develop
        trunk.checkout()
        self._repo.git.merge(
            hotfix_name,
            no_ff=True,
        )
        summary += [
            "Branch {} merged into {}".format(hotfix_name, trunk.name),
        ]

        # push to canon
        self.canon.push()
        self.canon.push(tags=True)
        summary += [
            "{}, {}, and tags have been pushed to {}".format(self.master.name, trunk.name, self.canon.name),
        ]

        for number in issue_numbers:
            try:
                number = int(number)
            except ValueError:
                continue

            issue = self._gh_repo.get_issue(number)
            issue.edit(state='closed')
            summary += [
                "Closed issue #{}".format(issue.number),
            ]

        if delete_hotfix_branch:
            self._repo.delete_head(hotfix_name)
            self.canon.push(
                hotfix_name,
                delete=True,
            )
            summary += [
                "Branch {} removed".format(hotfix_name),
            ]

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]

    @with_summary
    def contribute_hotfix(self, summary=None):
        if not (self.hotfix and self.hotfix.commit in self._repo.head.reference.object.iter_parents()):
            # Don't allow random branches to be contributed.
            print (
                "You are attempting to contribute a branch that is not a "
                "descendant of the current hotfix.\n"
                "Unfortunately, this isn't allowed."
            )
            return

        branch_name = self._repo.head.reference.name
        self._repo.git.push(
                self._cr.flowhub.structure.origin,
                branch_name,
                set_upstream=True,
        )

        if self.canon == self.origin:
            gh_parent = self._gh_repo
            base = self.hotfix.name
            head = branch_name
        else:
            gh_parent = self._gh_repo.parent
            base = self.hotfix.name
            head = "{}:{}".format(self._gh.get_user().login, branch_name)

        prs = [x for x in gh_parent.get_pulls('open') if x.head.label == head \
                    or x.head.label == "{}:{}".format(self._gh.get_user().login, head)]
        if prs:
            # If there's already a pull-request, don't bother hitting the gh api.
            summary += [
                "New commits added to existing pull-request"
                "\n\turl: {}".format(prs[0].issue_url)
            ]
            return

        pr = self._create_pull_request(base, head, gh_parent)
        summary += [
            "New pull request created: {} into {}"
            "\n\turl: {}".format(
                head,
                base,
                pr.issue_url,
            )
        ]

    def _open_issue(self, title=None, labels=None, create_branch=False,
        summary=None, return_values=False):
        if title is None:
            title = raw_input("Title for this issue: ")
        else:
            print "Title for this issue: ", title

        if labels is None:
            labels = []

        if summary is None:
            summary = []

        gh_labels = [l for l in self._gh_repo.get_labels() if l.name in labels]

        # Open the $EDITOR, if you can...
        descr_f = tempfile.NamedTemporaryFile(delete=False)
        descr_f.file.write(
            "\n\n# Write your description above. Remember - you can use GitHub markdown syntax!"
        )
        if self.__debug > 3:
            print "Temp file: ", descr_f.name
        # regardless, close the tempfile.
        descr_f.close()

        try:
            editor_result = subprocess.check_call(
                "$EDITOR {}".format(descr_f.name),
                shell=True
            )
        except OSError:
            if self.__debug > 2:
                print "Hmm...are you on Windows?"
            editor_result = 126

        if self.__debug > 3:
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

        if self.__debug > 3:
            print "Description used:\n", body

        issue = self._gh_repo.create_issue(
            title=title,
            body=body or "No description provided.",
            labels=gh_labels,
        )

        summary += [
            'Opened issue #{}: {}{}\n'
            '\turl: {}'.format(
                issue.number,
                title,
                '\n\t[{}]'.format(' '.join([l.name for l in gh_labels])) if gh_labels else '',
                issue.url,
            )
        ]

        if create_branch:
            feature_name = "{}-{}".format(
                issue.number,
                title.replace(' ', '-').lower(),
            )
            self._create_feature(
                name=feature_name,
                create_tracking_branch=False,
                summary=summary,
            )
        if return_values:
            return issue

    open_issue = with_summary(_open_issue)
