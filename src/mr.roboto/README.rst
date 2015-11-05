.. contents::

Introduction
============

DB
==

Pushes
------

Stores the pushes we did to plone packages

 * data (commit_info)
 * repo
 * branch
 * who
 * payload
 * date
 * internal_id

Jenkins Jobs
------------

Stores the jobs that are running on jenkins

 * push_internal_id
 * job_name (job on jenkins)
 * jk_id (push_internal_id + job_name)
 * type ('core', 'plip')


WebServices
===========

/run/corecommit

  Security : parameter based ?token=XXXXX
  It runs the jobs from jenkins responsible of the core-dev testing
  In case is a commit to coredev:
    * It sends a mail to plone-cvs if [fc] is not on commit message
    * It starts a job on jenkins plone if [ci skip] is not on commit message

/run/githubcommithooks

  Security : parameter based ?token=XXXXX
  Creates github post-commit hooks to all plone repositories in
  buildout.coredev sources.cfg.
