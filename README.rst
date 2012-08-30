=======
Flowhub
=======

Flowhub translates the workflow implemented by the excellent
`git-flow <http://github.com/nvie/gitflow>`_ Git add-on to GitHub.

Flowhub has no meaning outside of a Git repository. After installing,
you'll have access to the ``flowhub`` command:

.. code-block:: bash

    flowhub init
    # blah blah
    flowhub feature start <name-of-feature>


See ``flowhub -h`` and its descendants for more information.


What Can Flowhub Do?
--------------------

Flowhub keeps groups working in an orderly fashion, with minimal intrusion.

For Developers
~~~~~~~~~~~~~~

Let's examine a common use-case: you've forked another repository on GitHub
(totally coincidentally, this happens to be the case that Flowhub was written
for).

Suzy has forked a fellow developer's repository, and already has a clone of it
on her development box. She wants to keep her contributions orderly, and
(luckily!) the original repository adheres to a single-stable/single-dev branching
philosophy already (Flowhub doesn't require this, but it makes things easier).

Suzy decides to use Flowhub.

.. code-block:: bash

    cd /path/to/my/clone
    flowhub init

After answering all of Flowhub's questions, Suzy is ready to start working (she
decided to keep all of Flowhub's defaults).

.. code-block:: bash

    flowhub feature start suzy-feature-the-first
    Password for 'https://suzyongithub@github.com':
    Summary of actions:
        New branch feature/suzy-feature-the-first, from branch develop
        Checked out out branch feature/suzy-feature-the-first

After Suzy's been working for a while, she decides it's time to get some
feedback from the original repository. Flowhub makes this a cakewalk.

.. code-block:: bash

    flowhub feature publish # Since Suzy is still on her feature branch, Flowhub assumes that's the one to publish

Flowhub creates a pull-request for her, and reports the url so she can quickly
navigate to it.

After she's gotten some feedback and addressed it, she runs the same command.
Flowhub updates the pull-request for her.

For Managers
~~~~~~~~~~~~

After a while, Suzy is given push access to the original repository (the
maintainer cited her excellent branch organization as a key reason for the
promotion).

Now Suzy can make use of Flowhub's managerial commands.

A milestone has been reached in her project, and it's time to get ready to
release a new version.

.. code-block:: bash

    flowhub release start 0.3 # or whatever you want to tag the release as
    Summary of actions:
        New branch release/0.3 created, from branch develop
        Checked out branch release/0.3

this creates a new branch, off of develop, and sends it to github so that other
developers can start dotting i's and crossing t's. Flowhub will only allow one
release branch at a time.

When the release is polished to Suzy's satisfaction, she publishes the release:

.. code-block:: bash

    flowhub release publish # Suzy is on the release she wants to publish; she could also name it here.
    Message for this tag (0.3): Lotta cool stuff here!
    # Some passwords
    Summary of actions:
        Latest objects fetched from canon
        Branch release/0.3 merged into master
        New tag (0.3:"Lotta cool stuf here!") created at master's tip
        Branch release/0.3 merged into develop
        Branch release/0.3 removed
        master, develop, and tags have been pushed to canon
        Checked out branch develop
