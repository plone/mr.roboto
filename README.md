mr.roboto
=========

The main goal of mr.roboto is to maintain sync between jenkins and github, taking
care of the specific user cases of plone architecture.

Configuration
=============




Use Cases
=========

See log
-------

To see the log that's beeing proceessed

https://jenkins.plone.org:6543/log?token=XXXXX


Autoconfigure the github repositories that are on core-dev sources
------------------------------------------------------------------

It scans all the github repositories on core-dev sources and adds as hook the mr.roboto
webservices. It will clean all the hooks on plone core-dev packages.

Who to call :

https://jenkins.plone.org:6543/run/githubcommithooks?token=XXXXX

They are installed on the branch set on 

mr.roboto.views.run.ACTUAL_HOOKS_INSTALL_ON = '4.3'


Create core-dev jenkins jobs and clean jenkins
----------------------------------------------

It removes all the jenkins jobs that not Packages or Core and reconfigure Core tests again

Who to call :

https://jenkins.plone.org:6543/run/resetjenkins?token=XXXXX

Which jobs are reconfigured depends on :

mr.roboto.views.run.COREDEV_BRANCHES_TO_CHECK = ['4.2', '4.3', '4.4']

mr.roboto.views.run.PYTHON_VERSIONS = ['2.6', '2.7']


There is a commit to a package that's on the core-dev sources
-------------------------------------------------------------



There is a pull request to a package that's on the core-dev sources
-------------------------------------------------------------------



Jenkins Jobs
============

Jenkins jobs are automatic created based on templates on mr.roboto.templates

* plone.pt - template to create plone package jobs


WebServices
===========

/run/corecommit

  Security : parameter based ?token=XXXXX
  It runs the jobs from jenkins responsible of the core-dev testing

/run/githubcommithooks

  Security : parameter based ?token=XXXXX
  Creates github post-commit hooks to all plone repositories in
  buildout.coredev sources.cfg.

/run/createjenkinsjobs

  Security : parameter based ?token=XXXXX
  Creates all Jenkins jobs for Plone.