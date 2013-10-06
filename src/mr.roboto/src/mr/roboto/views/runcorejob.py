# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatetoken
from mr.roboto.security import validategithub
from mr.roboto.jenkinsutil import jenkins_core_job
from mr.roboto.jenkinsutil import jenkins_create_pull_job
from mr.roboto.jenkinsutil import jenkins_get_job_url
from mr.roboto.jenkinsutil import jenkins_build_job
from mr.roboto.jenkinsutil import jenkins_remove_job
from mr.roboto.jenkinsutil import jenkins_job_plip
from mr.roboto.jenkinsutil import jenkins_core_package_job
from mr.roboto.buildout import PloneCoreBuildout
from mr.roboto.subscriber import get_info_from_commit

from mr.roboto.db import CorePackages
from mr.roboto.db import CorePackage
from mr.roboto.db import JenkinsJob
from mr.roboto.db import JenkinsJobs
from mr.roboto.db import Push
from mr.roboto.db import Pushes

from mr.roboto.events import NewCoreDevBuildoutPush

from mr.roboto import templates, dir_for_kgs, static_dir

import transaction

import logging
import json
import uuid
import os


logger = logging.getLogger('mr.roboto')

runCoreTests = Service(
    name='Run core tests',
    path='/run/corecommit',
    description="Run the core-dev buildout"
)


# CORE-DEV PYTHON VERSIONS

OLD_PYTHON_VERSIONS = ['2.6', '2.7']
PYTHON_VERSIONS = ['2.7']


def add_log(request, who, message):
    logger.info(who + " " + message)


@runCoreTests.post()
@validategithub
def runFunctionCoreTests(request):
    """
    When we are called by GH we want to run the jenkins builds

    It's called for each push on the plone repo, so we look which tests needs to be runned for this repo:

    * Core Dev : it's on sources
    * PLIP : it's added as specific PLIP
    * Package : it's added as specific package

    """
    payload = json.loads(request.POST['payload'])

    # DB of jenkins jobs
    jenkins_jobs = JenkinsJobs(request.registry.settings['dm'])
    pushes = Pushes(request.registry.settings['dm'])

    # General Vars we need
    organization = payload['repository']['organization']
    repo_name = payload['repository']['name']

    repo = organization + '/' + repo_name
    branch = payload['ref'].split('/')[-1]

    # Create uuid for the push
    push_id = uuid.uuid4().hex

    # Going to run the core-dev tests
    # Who is doing the push ??

    if payload['pusher']['name'] == u'none':
        who = "NoBody <nobody@plone.org>"
    else:
        who = "%s <%s>" % (payload['pusher']['name'], payload['pusher']['email'])
    changeset = ""
    commits_info = []

    for commit in payload['commits']:
        # get the commit data structure
        commit_data = get_info_from_commit(commit)
        commits_info.append(commit_data)

        # prepare a changeset text message
        data = {
            'push': payload,
            'commit': commit,
            'files': '\n'.join(commit_data['files']),
            'diff': commit_data['diff'],
        }
        changeset += templates['jenkins_changeset.pt'](**data)

        # For logging
        message = 'Commit on ' + repo + ' ' + branch + ' ' + commit['id']
        add_log(request, commit_data['reply_to'], message)

    pushes[push_id] = Push(push_id, commits_info, repo=repo, branch=branch, who=who, payload=payload)

    changeset_file = open(static_dir + '/' + push_id, 'w')
    changeset_file.write(changeset)
    changeset_file.close()
    file_to_download = request.registry.settings['roboto_url'] + 'static/changeset/' + push_id

    params = {'plonechanges': file_to_download, 'repo': repo}
    params_package = {'plonechanges': file_to_download}

    # In case is a push to buildout-coredev
    if repo == 'plone/buildout.coredev':
        # Temporal hack to get correct versions
        if branch in ['4.2', '4.3']:
            pyversions = OLD_PYTHON_VERSIONS
        else:
            pyversions = PYTHON_VERSIONS

        # Subscribers to a git push event - so send mail
        request.registry.notify(NewCoreDevBuildoutPush(payload, request))

        for python_version in pyversions:
            # Run the complete coredev
            job_name = 'plone-' + branch + '-python-' + python_version
            message = 'Start ' + job_name + ' Jenkins Job'

            jk_job_id = push_id + '_' + job_name
            jenkins_jobs[jk_job_id] = JenkinsJob('core', jk_job_id, jk_name=job_name, push=push_id)
            transaction.commit()

            # Define the callback url for jenkins
            url = request.registry.settings['callback_url'] + 'corecommit?jk_job_id=' + jk_job_id


            # We run the JK job
            jenkins_core_job(request, job_name, url, payload=payload, params=params)

            add_log(request, who, message)

    else:
        # It's not a commit to coredev repo
        # Look at DB which plone version needs to run tests
        core_jobs = list(request.registry.settings['db']['core_package'].find({'repo': repo, 'branch': branch}))

        # Run the core jobs related with this commit on jenkins
        for core_job in core_jobs:
            # Temporal hack to get correct versions
            if core_job['plone_version'] in ['4.2', '4.3']:
                pyversions = OLD_PYTHON_VERSIONS
            else:
                pyversions = PYTHON_VERSIONS

            for python_version in pyversions:
                job_name = 'plone-' + core_job['plone_version'] + '-python-' + python_version
                message = 'Start ' + job_name + ' Jenkins Job'

                # Coredev.buildout job
                # Define the callback url for jenkins
                jk_job_id = push_id + '_' + job_name
                url = request.registry.settings['callback_url'] + 'corecommit?jk_job_id=' + jk_job_id
                jenkins_jobs[jk_job_id] = JenkinsJob('core', jk_job_id, jk_name=job_name, push=push_id)
                transaction.commit()
                jenkins_core_job(request, job_name, url, payload=payload, params=params)

                # Core package job
                # Define the callback url for jenkins
                jk_job_id = repo_name + '_' + push_id + '_' + job_name
                url = request.registry.settings['callback_url'] + 'corecommitkgs?jk_job_id=' + jk_job_id
                job_kgs_name = 'kgs-' + repo_name + '-' + job_name
                jenkins_jobs[jk_job_id] = JenkinsJob('corepackage', jk_job_id, jk_name=job_kgs_name, push=push_id)
                transaction.commit()

                # Convert 2.7 to 27 for python jenkins
                pyv = python_version.replace('.', '')

                # get sources for kgs
                folder_to_store_kgs = dir_for_kgs + '/' + job_name + '/'
                if os.access(folder_to_store_kgs, os.R_OK):
                    f = open(folder_to_store_kgs + 'snapshoot.cfg', 'r')
                    sources = f.read()
                    f.close()
                else:
                    sources = ""

                data = {
                    'description': 'Test %s with %s' % (repo, job_name),
                    'python_version': pyv,
                    'contact': who,
                    'plone_version': core_job['plone_version'],
                    'package_name': repo_name,
                    'sources': sources

                }
                jenkins_core_package_job(request, job_kgs_name, url, data, payload=payload, params=params_package)

                add_log(request, who, message)

        # Look at DB which PLIP jobs needs to run
        # We need to look if there is any PLIP job that needs to run tests
        plips = list(request.registry.settings['db']['plip'].find({'repo': [repo, branch]}))

        for plip in plips:
            # Run the JK jobs for each plip
            job_name = 'plip-' + plip['description']
            message = 'Start ' + job_name + ' Jenkins Job'

            # We create the JK job
            jk_job_id = push_id + '_' + job_name
            jenkins_jobs[jk_job_id] = JenkinsJob('plip', jk_job_id, jk_name=job_name, push=push_id)
            transaction.commit()

            # We create the JK job
            url = jenkins_job_plip(request, job_name, url, plip, payload=payload, params=params)
            # We set the jenkins job url on the plip
            plip['jk_url'] = url
            add_log(request, who, message)
            transaction.commit()

