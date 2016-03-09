=========
mr.roboto
=========

The main goal of mr.roboto is to maintain sync between jenkins and github, taking
care of the specific user cases of plone architecture.

Use Cases
=========

See log
-------

To see the log that's being processed

https://jenkins.plone.org/roboto/log?token=XXXXX


Autoconfigure the github repositories that are on core-dev sources
------------------------------------------------------------------

It scans all the github repositories on core-dev sources and adds as hook the mr.roboto
webservices. It will clean all the hooks on plone core-dev packages.

Who to call :

https://jenkins.plone.org/roboto/run/githubcommithooks?token=XXXXX


There is a commit to a package that's on the core-dev sources
-------------------------------------------------------------



There is a pull request to a package that's on the core-dev sources
-------------------------------------------------------------------


WebServices
===========

/run/corecommit

  Security : parameter based ?token=XXXXX
  It runs the jobs from jenkins responsible of the core-dev testing

/run/githubcommithooks

  Security : parameter based ?token=XXXXX
  Creates github post-commit hooks to all plone repositories in
  buildout.coredev sources.cfg.


Development
===========

To test changes locally,
do the following:

- rename ``development.ini.sample`` to ``development.ini`` and edit as needed
- run buildout::

      virtualenv .
      source bin/activate
      bin/buildout

- start pyramid::

      bin/pserve development.ini --reload

- *hack away!*
