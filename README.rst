flowhub
=======

Flowhub translates the workflow implemented by the excellent
`git-flow <http://www.github.com/nvie/gitflow>`_ Git add-on to GitHub.

Scott Chacon (of GitHub fame) points out that sometimes ``git-flow`` isn't the
best workflow for an agile team. Flowhub is cool with that, too - setting the
options one way gives you a translation of ``git-flow``, and setting them
a slightly different way gives you a translation of
`GitHub Flow <http://scottchacon.com/2011/08/31/github-flow.html>`_.

You can also get a hybrid of the two, if that floats your boat.

Outside of a Git repository, Flowhub is super-confused and refuses to work. As
far as I know, Flowhub does not integrate with any other Git clients. If it does,
that's a happy accident: Flowhub is designed as a command-line tool.

How do I get Flowhub?
---------------------------------

Great question! The easiest way is probably using the overworked and
under-appcreciated `pip <http://www.pip-installer.org/en/latest/>`_, which
is a very friendly way to install python packages in general.

Once you have pip on your system, simply run ``pip install flowhub``, and that
should be that. If you prefer the bleeding edge of Flowhub development, you can
get that too: simply clone this repository, checkout the ``develop``
branch, and run ``setup.py install`` (be ye warned, however: ``develop`` is not
guaranteed to be stable). There are very few dependencies -- check out the setup
script to see what they are.

After installing,
you'll have access to the ``flowhub`` command:

.. code-block:: bash

    flowhub init
    # blah blah
    flowhub feature start <name-of-feature>


See ``flowhub -h`` and its descendants for more information.

Flowhub definitely works on OSX and probably works on Linux (last I checked, it
works on Ubuntu), and might or might not work on Windows (a new frontier!).



What Can Flowhub Do?
--------------------

Flowhub keeps groups working in an orderly fashion, with minimal intrusion.

For Developers
~~~~~~~~~~~~~~

Let's examine a common use-case: you've forked another repository on GitHub
(totally coincidentally, this happens to be the case that Flowhub was written
for - though it doesn't require this set up).

init
++++

Suzy has forked a fellow developer's repository, and already has a clone of it
on her development box. She wants to keep her contributions orderly, and
(luckily!) the original repository adheres to a single-stable/single-dev branching
philosophy already (Flowhub doesn't require this, but it makes things easier).

Suzy decides to use Flowhub (she's got a bright future).

.. code-block:: bash

    cd /path/to/my/clone
    flowhub init

After answering all of Flowhub's questions, Suzy is ready to start working (she
decided to keep all of Flowhub's defaults).

feature start
+++++++++++++++

She's already got some ideas about how to improve the project:

.. code-block:: bash

    flowhub feature start suzy-feature-the-first
    Password for 'https://suzyongithub@github.com':

    Summary of actions:
     - New branch feature/suzy-feature-the-first, from branch develop
     - Checked out branch feature/suzy-feature-the-first

She's also come up with a solution to an existing issue:

.. code-block:: bash

    flowhub feature start -i 13 i-know-the-answer
    Password for 'https://suzyongithub@github.com':

    Summary of actions:
     - New branch feature/13-i-know-the-answer, from branch develop
     - Checked out branch feature/13-i-know-the-answer

When she's ready to publish, that branch will be tied to issue #13 on ``canon``.

feature publish
+++++++++++++++

After Suzy's been working for a while, she decides it's time to get some
feedback from the original repository. Flowhub makes this a cakewalk.

.. code-block:: bash

    flowhub feature publish # Since Suzy is still on her feature branch, Flowhub assumes that's the one to publish

Flowhub creates a pull-request for her, and reports the url so she can quickly
navigate to it.

When she's gotten some feedback and addressed it, she runs the same command.
Flowhub updates the pull-request for her.

feature abandon/accepted
++++++++++++++++++++++++

When her pull-request has been accepted, Suzy can run

.. code-block:: bash

    flowhub feature accepted

    Summary of actions:
     - Latest objects fetched from canon
     - Updated develop
     - Deleted feature/accepted-feature from local repository
     - Deleted feature/accepted-feature from origin
     - Checked out branch develop

from her feature branch, and Flowhub will clean things up a bit. She can also
specify a feature name, if she's not currently on the accepted branch.

If Suzy's feature is deemed a non-starter, and summarily rejected, Flowhub is
there to comfort her:

.. code-block:: bash

    flowhub feature abandon

    Summary of actions:
     - Deleted feature/abandoned-feature from local repository
     - Deleted feature/accepted-feature from origin
     - Checked out branch develop

Which will remove the feature branch she'd been working on.

The difference between ``accepted`` and ``abandon`` is that ``accepted`` will
complain if the feature branch hasn't been fully merged into your trunk branch;
``abandon`` doesn't care.

feature list
++++++++++++

At any time, Suzy can get a list of her current features' names (she's
been so prolific that she's lost track of them all).

.. code-block:: bash

    flowhub feature list
      suzy-feature-the-first
    * suzy-currently-checkedout-feature
      # ...
      suzy-feature-the-millionth

release/hotfix contribute
+++++++++++++++++++++++++

When it's time for a release, Flowhub has your back as well. Just branch off the
tip of the release, and work. When you're satisfied, run the ``release
contribute`` command *while that branch is checked out*:

.. code-block:: bash

    flowhub release contribute

It's very similar to the ``feature publish`` command, but the target of the
pull-request is the release branch, not the trunk.

``hotfix contribute`` does the same thing, but for hotfixes.

Both ``contribute`` commands won't allow you to contribute branches that aren't
descended from release/hotfix branch (as appropriate).

For Managers
~~~~~~~~~~~~

After a while, Suzy is given push access to the original repository (the
maintainer cited her excellent branch organization as a key reason for the
promotion).

Now Suzy can make use of Flowhub's managerial commands.

A milestone has been reached in her project, and it's time to get ready to
release a new version (Suzy's repository is a good fit for ``git-flow`` - if
Github-flow were a better match for her, she wouldn't need the managerial
commands at all).

.. code-block:: bash

    flowhub release start 0.3 # or whatever you want to tag the release as

    Summary of actions:
     - New branch release/0.3 created, from branch develop
     - Pushed branch release/0.3 to canon
     - Checked out branch release/0.3

    Bump the release version now!

this creates a new branch, off of develop, and sends it to github so that other
developers can start dotting i's and crossing t's. Flowhub will only allow one
release branch at a time.

When the release is polished to Suzy's satisfaction, she publishes the release:

.. code-block:: bash

    flowhub release publish # Suzy is on the release she wants to publish; she could also name it here.
    Message for this tag (0.3): Lotta cool stuff here!

    Summary of actions:
     - Latest objects fetched from canon
     - Branch release/0.3 merged into master
     - New tag (0.3:"Lotta cool stuf here!") created at master's tip
     - Branch release/0.3 merged into develop
     - master, develop, and tags have been pushed to canon
     - Branch release/0.3 removed
     - Checked out branch develop


A few days later, Suzy notices that a rare but seriously bad bug snuck
through testing, and is affecting users. Suzy doesn't panic - she has Flowhub:

.. code-block:: bash

    flowhub hotfix start 0.3.1

    Summary of actions:
     - Latest objects fetched from canon
     - Updated master
     - New branch hotfix/0.3.1 created, from branch master
     - Pushed hotfix/0.3.1 to canon
     - Checked out branch hotfix/0.3.1

    Bump the release version now!

Just like releases, Flowhub will only let you have one hotfix branch going at a
time.

When the bug's been killed, Suzy runs

.. code-block:: bash

    flowhub hotfix publish
    Message for this tag (0.3.1): Sorry, guys.

    Summary of actions:
     - Branch hotfix/0.3.1 merged into master
     - New tag (0.3.1:"Sorry, guys.") created at master's tip
     - Branch hotfix/0.3.1 merged into develop
     - master, develop and tags have been pushed to canon
     - Branch hotfix/0.3.1 removed
     - Checked out branch develop

If Suzy had been running a release branch at the time, the hotfix would have
been merged into that instead of her trunk; the bug would have been killed in
trunk when the release was published.
