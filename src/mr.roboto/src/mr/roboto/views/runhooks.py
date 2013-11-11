# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatetoken
from mr.roboto.security import validategithub
from mr.roboto.jenkinsutil import jenkins_core_job
from mr.roboto.jenkinsutil import jenkins_create_pull_job
from mr.roboto.jenkinsutil import jenkins_get_job_url
from mr.roboto.jenkinsutil import jenkins_build_job
from mr.roboto.jenkinsutil import jenkins_remove_job
from mr.roboto.buildout import PloneCoreBuildout
from mr.roboto.subscriber import get_info_from_commit

from mr.roboto.db import CorePackages
from mr.roboto.db import CorePackage
from mr.roboto.db import JenkinsJob
from mr.roboto.db import JenkinsJobs
from mr.roboto.db import PullRequest
from mr.roboto.db import PullRequests

import transaction

import logging
import json
import uuid


logger = logging.getLogger('mr.roboto')

def add_log(request, who, message):
    logger.info(who + " " + message)

createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description="Creates github post-commit hooks."
)


@createGithubPostCommitHooks.post()
@validatetoken
def createGithubPostCommitHooksView(request):
    # We should remove all the actual hooks
    github = request.registry.settings['github']
    roboto_url = request.registry.settings['roboto_url']
    actual_plone_versions = request.registry.settings['plone_versions']

    dm = request.registry.settings['dm']
    core_packages = CorePackages(dm)

    # Remove all core_packages
    request.registry.settings['db']['core_package'].remove({})
    # actual_packages = core_packages.keys()
    # for actual_package in actual_packages:
    #     del core_packages[actual_package]

    transaction.commit()

    core_packages = CorePackages(dm)
    # Clean Core Packages DB and sync to GH
    for plone_version in actual_plone_versions:

        # Add the core package to mongo
        buildout = PloneCoreBuildout(plone_version)
        sources = buildout.sources.keys()
        for source in sources:
            source_obj = buildout.sources[source]
            if source_obj.path is not None:
                core_packages[source] = CorePackage(source, source_obj.path, source_obj.branch, plone_version)

        transaction.commit()

    # hooks URL
    commit_url = roboto_url + 'run/corecommit'
    pull_url = roboto_url + 'run/pullrequest'

    messages = []
    # set hooks on github
    for repo in github.get_organization('plone').get_repos():

        hooks = repo.get_hooks()

        # Remove the old hooks
        for hook in hooks:

            #if hook.name == 'web' and (hook.config['url'].find(roboto_url) or hook.config['url'].find('jenkins.plone.org')):
            if hook.name == 'web' and hook.config['url'].find(roboto_url):
                add_log(request, 'github', 'Removing hook ' + str(hook.config))
                hook.delete()

        # Add the new hooks
        add_log(request, 'github', 'Creating hook ' + commit_url + ' and ' + pull_url)
        messages.append('Creating hook ' + commit_url)
        try:
            repo.create_hook('web', {'url': commit_url, 'secret': request.registry.settings['api_key']}, 'push', True)
            repo.create_hook('web', {'url': pull_url, 'secret': request.registry.settings['api_key']}, 'pull_request', True)
        except:
            pass
    return json.dumps(messages)
