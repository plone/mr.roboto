.. -*- coding: utf-8 -*-

.. contents::

============
Introduction
============

WebServices
===========

``/run/corecommit``
  Security: parameter based ``?token=XXXXX``
  It runs the jobs from jenkins responsible of the core-dev testing
  In case is a commit to coredev:
  
  * It starts a job on jenkins plone if [ci skip] is not on commit message

``/run/githubcommithooks``
  Security: parameter based ``?token=XXXXX``
  Creates github post-commit hooks to all plone repositories in buildout.coredev sources.cfg.
