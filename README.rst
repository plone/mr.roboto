.. -*- coding: utf-8 -*-

=========
mr.roboto
=========
The main goal of mr.roboto is to make sure `Plone's Jenkins CI <http://jenkins.plone.org>`_ test every single change made by Plone developers.

This way not only Plone contributors will be promptly notified (by Jenkins) that a change broke the tests,
but at the same time,
and most importantly,
they will be able to know exactly what change broke the build.

Use Cases
=========

See log
-------
To see the log that's being processed:

http://jenkins.plone.org/roboto/log?token=XXXXX

Autoconfigure hooks
-------------------
mr.roboto needs to get notified whenever a change has been made on a Plone core package,
so it can take all the necessary actions to ensure our CI system gets notified,
if needed,
and runs tests for certain Plone versions.

For that, mr.roboto needs to add a hook to all Plone Github repositories.

At the same time it removes all previously installed hooks to be sure no cruft is left behind.

To do so, call this URL:

http://jenkins.plone.org/roboto/run/githubcommithooks?token=XXXXX

There is a commit to a package that's on the core-dev sources
-------------------------------------------------------------
The hook installed on all Plone Github repositories notify this end-point whenever a change happens in them.

This way mr.roboto can make all the needed actions to ensure our CI setup is notified and runs the necessary jobs.

The URL that's being called is:

http://jenkins.plone.org/roboto/run/corecommit?token=XXXXX

Get sources and checkouts
-------------------------
For debugging purposes,
knowing what exactly mr.roboto has in its sources and checkouts can be really useful.

http://jenkins.plone.org/roboto/sources.json

http://jenkins.plone.org/roboto/checkouts.json

Branches overview
-----------------
Get an overview of which branch of each package is being used on any plone release.

http://jenkins.plone.org/roboto/branches

Update sources and checkouts
----------------------------
If there is something wrong with sources or checkouts,
or they are empty (new deployment),
you can force them to be created:

http://jenkins.plone.org/roboto/update-sources-and-checkouts?token=XXX

Development
===========
To test mr.roboto locally,
do the following:

- rename ``development.ini.sample`` to ``development.ini`` and edit as needed
- run buildout::

      virtualenv .
      source bin/activate
      bin/buildout

- start pyramid::

      bin/pserve development.ini --reload

- *hack away!*
