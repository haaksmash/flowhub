#!/usr/bin/env python
import argparse
import commands
from ConfigParser import NoOptionError, NoSectionError
import getpass
import git
from github import Github
import warnings

__version__ = "0.1"

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

    def create_feature(self, name=None, create_tracking_branch=True):
        if name is None:
            raise RuntimeError("Please provide a feature name.")

        if self.__debug > 0:
            print "creating new feature branch..."
        # Checkout develop
        # checkout -b feature_prefix+branch_name
        # push -u origin feature_prefix+branch_name

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'feature'),
            name
        )
        self._repo.create_head(
            branch_name,
            commit=self._repo.heads.develop,  # Requires a develop branch.
        )

        if create_tracking_branch:
            if self.__debug > 0:
                print "Adding a tracking branch to your GitHub repo"
            self._repo.git.push(
                self._cr.get('flowhub "structure"', 'origin'),
                branch_name,
                set_upstream=True
            )

        branch = [x for x in self._repo.branches if x.name == branch_name][0]

        # Checkout the branch.
        branch.checkout()

        print '\n'.join((
            "summary of actions: ",
            "\tnew branch {} created, from branch {}".format(
                branch_name,
                self._cr.get('flowhub "structure"', 'develop')
            ),
            "\tchecked out branch {}".format(branch_name),
        ))

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

        else:
            raise RuntimeError("no feature with name {}".format(name))

    def abandon_feature(self, name=None):
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.get('flowhub "prefix"', 'feature') not in name:
                raise RuntimeError("Please provide a feature name, or switch to a feature branch.")

            name = name.replace(self._cr.get('flowhub "prefix"', 'feature'), '')

        if self.__debug > 0:
            print "abandoning feature branch..."

        # checkout develop
        # branch -D feature_prefix+name
        # push --delete origin feature_prefix+name

        head = [x for x in self._repo.heads if x.name == self._cr.get('flowhub "structure"', 'develop')][0]
        head.checkout()

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'feature'),
            name,
        )

        self._repo.delete_head(branch_name)
        self._repo.git.push(
            self._cr.get('flowhub "structure"', 'origin'),
            branch_name,
            delete=True,
        )

        print "\n".join((
            "summary of actions: ",
            "\tdeleted branch {} locally and from remote {}".format(
                branch_name,
                self._cr.get('flowhub "structure"', 'origin')
            ),
            "\tchecked out branch {}".format(
                self._cr.get('flowhub "structure"', 'develop'),
            ),
        ))

    def publish_feature(self, name):
        if name is None:
            # If no name specified, try to use the currently checked-out branch,
            # but only if it's a feature branch.
            name = self._repo.head.reference.name
            if self._cr.get('flowhub "prefix"', 'feature') not in name:
                raise RuntimeError("please provide a feature name, or switch to a feature branch.")

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

        base = self._cr.get('flowhub "structure"', 'develop')
        head = "{}:{}".format(self._gh.get_user().login, branch_name)

        prs = [x for x in self._gh_repo.parent.get_pulls('open') if x.head.label == head]
        if prs:
            # If there's already a pull-request, don't bother hitting the gh api.
            print "new commits added to existing pull-request."
            print "url: {}".format(prs[0].issue_url)
            return

        print "setting up new pull-request"
        is_issue = raw_input("Is this feature answering an issue? [y/N] ") == 'y'

        if not is_issue:
            title = raw_input("Title: ")
            body = raw_input("Description (remember, you can use GitHub markdown):\n")

            if self.__debug > 1:
                print (title, body, base, head)
            pr = self._gh_repo.parent.create_pull(
                title=title,
                body=body,
                base=base,
                head=head,
            )
        else:
            issue_number = raw_input("Issue number: ")
            issue = self._gh_repo.parent.get_issue(int(issue_number))
            pr = self._gh_repo.parent.create_pull(
                issue=issue,
                base=base,
                head=head,
            )
        print "url: {}".format(pr.issue_url)

    def start_release(self, name):
        # checkout develop
        # if already release branch, abort.
        # checkout -b relase_prefix+branch_name
        if name is None:
            raise RuntimeError("Please provide a release name.")

        if any([x for x in self._repo.branches if x.name.startswith(self._cr.get('flowhub "prefix"', 'release'))]):
            raise RuntimeError("You already have a release in the works - please finish that one.")

        if self.__debug > 0:
            print "creating new release branch..."
        # Checkout develop
        # checkout -b feature_prefix+branch_name
        # push -u origin feature_prefix+branch_name

        branch_name = "{}{}".format(
            self._cr.get('flowhub "prefix"', 'release'),
            name
        )
        self._repo.create_head(
            branch_name,
            commit=self._repo.heads.develop,  # Requires a develop branch.
        )

        if self.__debug > 0:
            print "Adding a tracking branch to your GitHub repo"
        self._repo.git.push(
            self._cr.get('flowhub "structure"', 'canon'),
            branch_name,
            set_upstream=True
        )

        branch = [x for x in self._repo.branches if x.name == branch_name][0]

        # Checkout the branch.
        branch.checkout()

        print '\n'.join((
            "Summary of actions: ",
            "\tNew branch {} created, from branch {}".format(
                branch_name,
                self._cr.get('flowhub "structure"', 'develop')
            ),
            "\tChecked out branch {}".format(branch_name),
        ))

    def stage_release(self):
        print '\n'.join((
            "Summary of actions: ",
            "\tRelease branch sent off to stage",
            "\tRelease branch checked out and refreshed on stage.",
        ))

    def publish_release(self, name=None):
        # fetch canon
        # checkout master
        # merge canon master
        # merge --no-ff release
        # tag
        # checkout develop
        # merge canon develop
        # merge --no-ff release
        # push --tags canon
        # delete release branches
        # git push origin --delete name
        pass

    def cleanup_branches(self):
        # hotfixes: remove from origin, local if match not found on canon
        # releases: remove from origin, local if match not found on canon
        # features: if pull request found and accepted, delete from local and origin
        pass

    def create_hotfix(self):
        # Checkout master
        # if already hotfix branch, abort.
        # checkout -b hotfix_prefix+branch_name
        pass

    def apply_hotfix(self):
        # pull canon
        # checkout master
        # merge --no-ff hotfix
        # tag
        # checkout develop
        # merge --no-ff hotfix
        # push --tags canon
        # delete hotfix branches
        pass


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
        engine.publish_feature(name=args.name)

    elif args.action == 'abandon':
        engine.abandon_feature(
            name=args.name,
        )

    else:
        raise RuntimeError("Unimplemented command for features: {}".format(args.action))


def handle_hotfix_call(args, engine):
    if args.verbosity > 2:
        print "handling hotfix"

    if False:
        pass
    else:
        raise RuntimeError("Unimplemented command for hotfixes: {}".format(args.action))


def handle_release_call(args, engine):
    if args.verbosity > 2:
        print "handling release"

    if args.action == 'start':
        engine.start_release(name=args.name)
    else:
        raise RuntimeError("Unimplemented command for releases: {}".format(args.action))


def handle_cleanup_call(args, engine):
    if args.verbosity > 2:
        print "handling cleanup"

    if False:
        pass
    else:
        raise RuntimeError("Unimplemented command for cleanups: {}".format(args.action))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', action="store", type=int, default=0)
    parser.add_argument('--no-gh', action='store_true', default=False)

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

    #
    # Hotfixes
    #
    hotfix_subs = hotfix.add_subparsers(dest='action')

    hstart = hotfix_subs.add_parser('start',
        help="start a new hotfix branch")
    apply = hotfix_subs.add_parser('apply',
        help="apply a hotfix branch to master and develop branches")

    #
    # Releases
    #
    release_subs = release.add_subparsers(dest='action')

    rstart = release_subs.add_parser('start',
        help="start a new release branch")
    rstart.add_argument('name', help="name of the release branch.")

    rstage = release_subs.add_parser('stage',
        help="send a release branch to a staging environment")

    rpublish = release_subs.add_parser('publish',
        help="merge a release branch into master and develop branches")
    rpublish.add_argument('name', nargs='?',
        help="name of release to publish. if not specified, current branch is assumed.")

    rabandon = release_subs.add_parser('abandon',
        help='abort a release branch')
    rabandon.add_argument('name', nargs='?',
        help='name of release to abandon. if not specified, current branch is assumed.')
    #
    # Cleanup
    #
    cleanup_subs = cleanup.add_subparsers()

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
