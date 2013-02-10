.. contents::

Introduction
============

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
