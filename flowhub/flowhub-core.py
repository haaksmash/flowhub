#!/usr/bin/env python
import argparse
import commands
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
import getpass
import git
from github import Github
import os


class Engine(object):
    DEFAULT_CONF = "{}/.flowhub.cnf".format(os.getenv('HOME'))

    def __init__(self, config_file=None, debug=0):
        self.__debug = debug
        if config_file is not None:
            self._config = config_file
        else:
            self._config = self.DEFAULT_CONF

        self._c = SafeConfigParser()
        self._c.read(self.DEFAULT_CONF)

        self._gh = None
        if self.__debug > 0:
            print "Authorizing engine..."
        self.do_auth()

        self._repo = self._gh.get_user().get_repo(self._c.get('structure', 'repo'))

    def do_auth(self):
        """Generates the authorization to do things with github."""
        try:
            token = self._c.get('auth', 'token')
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
            self._gh = Github(raw_input("Username: "), getpass.getpass())

            auth = self._gh.get_user().create_authorization(
                'public_repo',
                'Flowhub Client',
            )
            token = auth.token

            if not self._c.has_section('auth'):
                if self.__debug > 1:
                    print "Adding 'auth' section"
                self._c.add_section('auth')

            self._c.set('auth', 'token', token)

            if not self._c.has_section('structure'):
                if self.__debug > 1:
                    print "Adding 'structure' section"
                self._c.add_section('structure')

            repo_name = raw_input("Repository name for this flowhub: ")

            self._c.set('structure', 'repo', repo_name)

            feature_prefix = raw_input("Prefix for feature branches [feature/]: ") or 'feature/'
            self._c.set('structure', 'feature_prefix', feature_prefix)
            release_prefix = raw_input("Prefix for releast branches [release/]: ") or "release/"
            self._c.set('structure', 'release_prefix', release_prefix)
            hotfix_prefix = raw_input("Prefix for hotfix branches [hotfix/]: ") or "hotfix/"
            self._c.set('structure', 'hotfix_prefix', hotfix_prefix)

            github_remote = raw_input("What is the name of the github remote? ")
            self._c.set('structure', 'gh_remote', github_remote)

            self.__write_conf()

    def __write_conf(self):
        with open(self._config, 'wb') as f:
            if self.__debug > 0:
                print "Storing configuration in {}".format(self._config)
            self._c.write(f)

    def publish_feature(self):
        repo_dir = commands.getoutput("git rev-parse --show-toplevel")
        if repo_dir.startswith('fatal'):
            raise RuntimeError("You don't appear to be in a git repository.")

        repo = git.Repo(repo_dir)
        gh = repo.remote(self._c.get('structure', 'gh_remote'))

    def create_release(self):
        pass

    def create_hotfix(self):
        # Checkout master
        # checkout -b hotfix_prefix+branch_name
        pass

    def create_feature(self):
        # Checkout develop
        # checkout -b feature_prefix+branch_name
        pass

    def rollback_branch(self, branch_name='master'):
        pass

    def prepare_release(self):
        pass

    def publish_release(self):
        pass
