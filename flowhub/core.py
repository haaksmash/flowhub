#!/usr/bin/env python
import argparse
import commands
from ConfigParser import NoOptionError, NoSectionError
import getpass
import git
from github import Github
import warnings

from decorators import with_summary

class Engine(object):

    def __init__(self, debug=0, skip_auth=False):
        self.__debug = debug

        self._repo = self._get_repo()

        self._cw = self._repo.config_writer()
        self._cr = self._repo.config_reader()

        self._gh = None
        if not skip_auth:
            if self.__debug > 0:
                print "Authorizing engine..."
            self.do_auth()
            # Refresh the read-only reader.
            self._cr = self._repo.config_reader()

            self._gh_repo = self._gh.get_user().get_repo(self._cr.get('flowhub "structure"', 'name'))

            if self._gh.rate_limiting[0] < 100:
                warnings.warn("You are close to exceeding your GitHub access rate; {} left out of {} initially".format(*self._gh.rate_limiting))
        else:
            if self.__debug > 0:
                print "Skipping auth - GitHub accesses will fail."

    def do_auth(self):
        """Generates the authorization to do things with github."""
        try:
            token = self._cr.get('flowhub "auth"', 'token')
            self._gh = Github(token)
            if self.__debug > 0:
                print "GitHub Engine authorized by token in settings."
        except (NoSectionError, NoOptionError):
            if self.__debug > 0:
                print "No token - generating new one."

            print (
                "This appears to be the first time you've used Flowhub; "
                "we'll have to do a little bit of setup."
            )
            self._cw.add_section('flowhub "auth"')
            self._gh = Github(raw_input("Username: "), getpass.getpass())

            auth = self._gh.get_user().create_authorization(
                'public_repo',
                'Flowhub Client',
            )
            token = auth.token

            self._cw.set('flowhub "auth"', 'token', token)

            self._cw.add_section('flowhub "structure"')

            self._cw.set('flowhub "structure"', 'name',
                raw_input("Repository name for this flowhub: "))
            self._cw.set('flowhub "structure"', 'origin',
                raw_input("Name of your github remote? [origin] ") or 'origin')
            self._cw.set('flowhub "structure"', 'canon',
                raw_input('Name of the organization remote? [canon] ') or 'canon')

            self._cw.set('flowhub "structure"', 'master',
                raw_input("Name of the stable branch? [master] ") or 'master')
            self._cw.set('flowhub "structure"', 'develop',
                raw_input("Name of the development branch? [develop] ") or 'develop')

            self._cw.add_section('flowhub "prefix"')

            feature_prefix = raw_input("Prefix for feature branches [feature/]: ") or 'feature/'
            self._cw.set('flowhub "prefix"', 'feature', feature_prefix)
            release_prefix = raw_input("Prefix for releast branches [release/]: ") or "release/"
            self._cw.set('flowhub "prefix"', 'release', release_prefix)
            hotfix_prefix = raw_input("Prefix for hotfix branches [hotfix/]: ") or "hotfix/"
            self._cw.set('flowhub "prefix"', 'hotfix', hotfix_prefix)

            self.__write_conf()

            print '\n'.join((
                "You can change these settings just like all git settings, using the\n",
                "\tgit config\n",
                "command."
            ))

            self._setup_repository_structure()

    def __write_conf(self):
        self._cw.write()

    @property
    def develop(self):
        return [x for x in self._repo.heads if x.name == self._cr.get('flowhub "structure"', 'develop')][0]

    @property
    def master(self):
        return [x for x in self._repo.heads if x.name == self._cr.get('flowhub "structure"', 'master')][0]

    @property
    def origin(self):
        return self._repo.remote(self._cr.get('flowhub "structure"', 'origin'))

    @property
    def canon(self):
        return self._repo.remote(self._cr.get('flowhub "structure"', 'canon'))

    @property
    def release(self):
        releases = [x for x in self._repo.branches if x.name.startswith(
                self._cr.get('flowhub "prefix"', 'release'),
            )]

        if releases:
            return releases[0]
        else:
            return None

    @property
    def hotfix(self):
        hotfixes = [x for x in self._repo.branches if x.name.startswith(
                self._cr.get('flowhub "prefix"', 'hotfix'),
            )]

        if hotfixes:
            return hotfixes[0]
        else:
            return None

    def setup_repository_structure(self):
        # make the repo...correct.
        pass

    def _get_repo(self):
        """Get the repository of this directory, or error out if not found"""
        repo_dir = commands.getoutput("git rev-parse --show-toplevel")
        if repo_dir.startswith('fatal'):
            raise RuntimeError("You don't appear to be in a git repository.")

        repo = git.Repo(repo_dir)
        return repo

    @with_summary
    def create_feature(self, name=None, create_tracking_branch=True, summary=None):
        if name is None:
            raise RuntimeError("Please provide a feature name.")

        if self.__debug > 0:
            print "Creating new feature branch..."
        # Checkout develop
        # checkout -b feature_prefix+branch_name
        # push -u origin feature_prefix+branch_name

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'feature'),
            name
        )
        self._repo.create_head(
            branch_name,
            commit=self.develop,  # Requires a develop branch.
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self._cr.get('flowhub "structure"', 'develop')
            )
        ]

        if create_tracking_branch:
            if self.__debug > 0:
                print "Adding a tracking branch to your GitHub repo"
            self._repo.git.push(
                self._cr.get('flowhub "structure"', 'origin'),
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

    def work_feature(self, name=None):
        """Simply checks out the feature branch for the named feature."""
        if name is None:
            raise RuntimeError("please provide a feature name.")

        if self.__debug > 0:
            print "switching to a feature branch..."

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'feature'),
            name
        )
        branches = [x for x in self._repo.branches if x.name == branch_name]
        if branches:
            branch = branches[0]
            branch.checkout()
            print "Switched to branch '{}'".format(branch.name)

        else:
            raise RuntimeError("No feature with name {}".format(name))

    @with_summary
    def accept_feature(self, name=None, summary=None):
        return_branch = self._repo.head.reference
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.get('flowhub "prefix"', 'feature') not in name:
                raise RuntimeError("Please provide a feature name, or switch to the feature branch you want to mark as accepted.")

            name = name.replace(self._cr.get('flowhub "prefix"', 'feature'), '')
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
            self._cr.get('flowhub "prefix"', 'feature'),
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
            if self._cr.get('flowhub "prefix"', 'feature') not in name:
                raise RuntimeError("Please provide a feature name, or switch to the feature branch you want to abandon.")

            name = name.replace(self._cr.get('flowhub "prefix"', 'feature'), '')
            return_branch = self.develop

        if self.__debug > 0:
            print "Abandoning feature branch..."

        # checkout develop
        # branch -D feature_prefix+name
        # push --delete origin feature_prefix+name

        return_branch.checkout()

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'feature'),
            name,
        )

        self._repo.delete_head(
            branch_name,
            force=True,
        )
        summary += [
            "Deleted branch {} locally and from remote {}".format(
                branch_name,
                self._cr.get('flowhub "structure"', 'origin')
            ),
        ]

        self._repo.git.push(
            self._cr.get('flowhub "structure"', 'origin'),
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
            if self._cr.get('flowhub "prefix"', 'feature') not in name:
                raise RuntimeError("please provide a feature name, or switch to the feature branch you want to publish.")

            name = name.replace(self._cr.get('flowhub "prefix"', 'feature'), '')

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'feature'),
            name
        )
        self._repo.git.push(
                self._cr.get('flowhub "structure"', 'origin'),
                branch_name,
                set_upstream=True
        )
        summary += [
            "Updated {}/{}".format(self.origin.name, branch_name)
        ]

        # if this isn't a fork, we have slightly different sha's.
        if self.canon == self.origin:
            gh_parent = self._gh_repo
            base = self.develop.name
            head = branch_name
        else:
            gh_parent = self._gh_repo.parent
            base = self.develop.name
            head = "{}:{}".format(self._gh.get_user().login, branch_name)

        prs = [x for x in gh_parent.get_pulls('open') if x.head.label == head]
        if prs:
            # If there's already a pull-request, don't bother hitting the gh api.
            summary += [
                "New commits added to existing pull-request"
                "\n\turl: {}".format(prs[0].issue_url)
            ]
            return

        if self.__debug > 1:
            print "setting up new pull-request"
        is_issue = raw_input("Is this feature answering an issue? [y/N] ") == 'y'

        if not is_issue:
            title = raw_input("Title: ")
            body = raw_input("Description (remember, you can use GitHub markdown):\n")

            if self.__debug > 1:
                print (title, body, base, head)
            pr = gh_parent.create_pull(
                title=title,
                body=body,
                base=base,
                head=head,
            )
        else:
            issue_number = raw_input("Issue number: ")
            issue = gh_parent.get_issue(int(issue_number))
            pr = gh_parent.create_pull(
                issue=issue,
                base=base,
                head=head,
            )
        summary += [
            "New pull request created: {} into {}"
            "\n\turl: {}".format(
                head,
                base,
                pr.issue_url)
        ]

    def list_features(self):
        for branch in self._repo.branches:
            if not branch.name.startswith(self._cr.get('flowhub "prefix"', 'feature')):
                continue
            display = '{}'.format(
                branch.name.replace(
                    self._cr.get('flowhub "prefix"', 'feature'),
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
            raise RuntimeError("Please provide a release name.")

        if any([x for x in self._repo.branches if x.name.startswith(self._cr.get('flowhub "prefix"', 'release'))]):
            raise RuntimeError("You already have a release in the works - please finish that one.")

        if self.__debug > 0:
            print "Creating new release branch..."

        # checkout develop
        # checkout -b release/name

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'release'),
            name
        )
        self._repo.create_head(
            branch_name,
            commit=self.develop,
        )
        summary += [
            "New branch {} created, from branch {}".format(
                branch_name,
                self._cr.get('flowhub "structure"', 'develop')
            ),
        ]

        if self.__debug > 0:
            print "Adding a tracking branch to your GitHub repo"
        self.canon.push(
            "{0}:{0}".format(branch_name),
            set_upstream=True
        )
        summary += [
            "Pushed {} to {}".format(branch_name, self.canon.name),
        ]

        branch = [x for x in self._repo.branches if x.name == branch_name][0]

        # Checkout the branch.
        branch.checkout()
        summary += [
            "Checked out branch {}"
            "\n\nBump the release version now!".format(branch_name),
        ]

    @with_summary
    def stage_release(self, summary=None):
        summary += [
            "Release branch sent off to stage",
        ]
        summary += [
            "Release branch checked out and refreshed on stage.",
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
            if self._cr.get('flowhub "prefix"', 'release') not in name:
                raise RuntimeError("please provide a release name, or switch to the release branch you want to publish.")

            name = name.replace(self._cr.get('flowhub "prefix"', 'release'), '')
            return_branch = self.develop

        release_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'release'),
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
        tag_message = raw_input("Message for this tag ({}): ".format(name)),
        self._repo.create_tag(
            path=name,
            ref=self.master,
            message=tag_message
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
    def cleanup_branches(self, summary=None):
        # hotfixes: remove from origin, local if match not found on canon
        # releases: remove from origin, local if match not found on canon
        for branch in self._repo.branches:
            if branch.name.startswith(self._cr.get('flowhub "prefix"', 'feature')):
                # Feature branches get removed if they're fully merged in to something else.
                # NOTE: this will delete branch references that have no commits in them.
                try:
                    self._repo.delete_head(branch.name)
                    summary += [
                        "Deleted local branch {}"
                    ]
                    remote_branch = branch.tracking_branch()
                    if remote_branch:
                        # get rid of the 'origin/' part of the remote name
                        remote_name = '/'.join(remote_branch.name.split('/')[1:])
                        self.origin.push(
                            remote_name,
                            delete=True,
                        )
                        summary[-1] += ' and remote branch {}'.format(remote_branch.name)

                except git.GitCommandError:
                    continue

    @with_summary
    def start_hotfix(self, name, summary=None):
        # Checkout master
        # if already hotfix branch, abort.
        # checkout -b hotfix_prefix+branch_name
        if name is None:
            raise RuntimeError("Please provide a release name.")

        if any([x for x in self._repo.branches if x.name.startswith(self._cr.get('flowhub "prefix"', 'hotfix'))]):
            raise RuntimeError("You already have a hotfix in the works - please finish that one.")

        if self.__debug > 0:
            print "Creating new hotfix branch..."

        # checkout develop
        # checkout -b release/name

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'hotfix'),
            name
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
                self.master.name
            ),
        ]

        if self.__debug > 0:
            print "Adding a tracking branch to your GitHub repo"
        self.canon.push(
            "{0}:{0}".format(branch_name),
            set_upstream=True
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
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.get('flowhub "prefix"', 'hotfix') not in name:
                raise RuntimeError("please provide a hotfix name, or switch to the hotfix branch you want to publish.")

            name = name.replace(self._cr.get('flowhub "prefix"', 'hotfix'), '')
            return_branch = self.develop

        hotfix_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'hotfix'),
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
        tag_message = raw_input("Message for this tag ({}): ".format(name)),
        self._repo.create_tag(
            path=name,
            ref=self.master,
            message=tag_message
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
            "{}, {}, and tags have been pushed to {}".format(self.master.name, self.develop.name, self.canon.name),
        ]

        if delete_hotfix_branch:
            self._repo.delete_head(hotfix_name)
            self.canon.push(
                hotfix_name,
                delete=True,
            )
            summary += [
                "Branch {} {}".format(hotfix_name, 'removed' if delete_hotfix_branch else "still available"),
            ]

        return_branch.checkout()
        summary += [
            "Checked out branch {}".format(return_branch.name),
        ]


def handle_init_call(args, engine):
    if args.verbosity > 2:
        print "handling init"

    engine.setup_repository_structure()


def handle_feature_call(args, engine):
    if args.verbosity > 2:
        print "handling feature"
    if args.action == 'start':
        engine.create_feature(
            name=args.name,
            create_tracking_branch=(not args.no_track),
        )

    elif args.action == 'work':
        engine.work_feature(name=args.name)

    elif args.action == 'publish':
        try:
            engine.publish_feature(name=args.name)
        except AssertionError:
            # This is janky as shit, but running twice fixes it.
            # see #14
            engine.publish_feature(name=args.name)
    elif args.action == 'abandon':
        engine.abandon_feature(
            name=args.name,
        )

    elif args.action == 'accepted':
        try:
            engine.accept_feature(
                name=args.name,
            )
        except AssertionError:
            # see #14
            engine.accept_feature(
                name=args.name,
            )
    elif args.action == 'list':
        engine.list_features()
    else:
        raise RuntimeError("Unimplemented command for features: {}".format(args.action))


def handle_hotfix_call(args, engine):
    if args.verbosity > 2:
        print "handling hotfix"

    if args.action == 'start':
        engine.start_hotfix(
            name=args.name,
        )
    elif args.action == 'publish':
        engine.publish_hotfix(
            name=args.name,
        )
    else:
        raise RuntimeError("Unimplemented command for hotfixes: {}".format(args.action))


def handle_release_call(args, engine):
    if args.verbosity > 2:
        print "handling release"

    if args.action == 'start':
        engine.start_release(
            name=args.name,
        )
    elif args.action == 'publish':
        engine.publish_release(
            name=args.name,
            delete_release_branch=(not args.no_cleanup),
        )
    else:
        raise RuntimeError("Unimplemented command for releases: {}".format(args.action))


def handle_cleanup_call(args, engine):
    if args.verbosity > 2:
        print "handling cleanup"

    engine.cleanup_branches()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', action="store", type=int, default=0)
    parser.add_argument('--no-gh', action='store_true', default=False,
        help='do not talk to GitHub',)

    subparsers = parser.add_subparsers(dest="subparser")
    init = subparsers.add_parser('init',
        help="set up a repository to use flowhub",)
    feature = subparsers.add_parser('feature',
        help="do feature-related things",)
    hotfix = subparsers.add_parser('hotfix',
        help="do hotfix-related things",)
    release = subparsers.add_parser('release',
        help="do release-related things",)
    cleanup = subparsers.add_parser('cleanup',
        help="do repository-cleanup related things",)

    #
    # Features
    #
    feature_subs = feature.add_subparsers(dest='action')

    fstart = feature_subs.add_parser('start',
        help="start a new feature branch")
    fstart.add_argument('name', help="name of the feature")
    fstart.add_argument('--no-track', default=False, action='store_true',
        help="do *not* set up a tracking branch on origin.")

    fwork = feature_subs.add_parser('work',
        help="switch to a different feature (by name)")
    fwork.add_argument('name', help="name of feature to switch to")

    fpublish = feature_subs.add_parser('publish',
        help="send the current feature branch to origin and create a pull-request")
    fpublish.add_argument('name', nargs='?',
        default=None,
        help='name of feature to publish. If not given, uses current feature')

    fabandon = feature_subs.add_parser('abandon',
        help="remove a feature branch completely"
    )
    fabandon.add_argument('name', nargs='?',
        default=None,
        help="name of the feature to abandon. If not given, uses current feature")
    faccepted = feature_subs.add_parser('accepted',
        help="declare that a feature was accepted into the trunk")
    faccepted.add_argument('name', nargs='?',
        default=None,
        help="name of the accepted feature. If not given, assumes current feature")
    flist = feature_subs.add_parser('list',
        help='list the feature names on this repository')

    #
    # Hotfixes
    #
    hotfix_subs = hotfix.add_subparsers(dest='action')

    hstart = hotfix_subs.add_parser('start',
        help="start a new hotfix branch")
    hstart.add_argument('name',
        help="name (and tag) for the hotfix")
    hpublish = hotfix_subs.add_parser('publish',
        help="publish the hotfix to production and trunk")
    hpublish.add_argument('name', nargs='?',
        help="name of hotfix to publish. If not given, uses current branch.")

    #
    # Releases
    #
    release_subs = release.add_subparsers(dest='action')

    rstart = release_subs.add_parser('start',
        help="start a new release branch")
    rstart.add_argument('name', help="name (and tag) of the release branch.")

    rstage = release_subs.add_parser('stage',
        help="send a release branch to a staging environment")

    rpublish = release_subs.add_parser('publish',
        help="publish a release branch to production and trunk")
    rpublish.add_argument('name', nargs='?',
        help="name of release to publish. if not specified, current branch is assumed.")
    rpublish.add_argument('--no-cleanup', action='store_true',
        default=False,
        help="do not delete the release branch after a successful publish",
    )

    rabandon = release_subs.add_parser('abandon',
        help='abort a release branch')
    rabandon.add_argument('name', nargs='?',
        help='name of release to abandon. if not specified, current branch is assumed.')
    #
    # Cleanup
    #
    args = parser.parse_args()
    if args.verbosity > 2:
        print "Args: ", args

    e = Engine(debug=args.verbosity, skip_auth=args.no_gh)

    if args.subparser == 'feature':
        handle_feature_call(args, e)

    elif args.subparser == 'hotfix':
        handle_hotfix_call(args, e)

    elif args.subparser == 'release':
        handle_release_call(args, e)

    elif args.subparser == 'cleanup':
        handle_cleanup_call(args, e)

    elif args.subparser == 'init':
        handle_init_call(args, e)

    else:
        raise RuntimeError("Unrecognized command: {}".format(args.subparser))

if __name__ == "__main__":
    run()
