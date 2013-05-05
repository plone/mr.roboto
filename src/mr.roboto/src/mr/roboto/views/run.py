# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatetoken
from mr.roboto.security import validategithub
from mr.roboto.jenkinsutil import jenkins_core_job
from mr.roboto.jenkinsutil import jenkins_create_pull_job
from mr.roboto.jenkinsutil import jenkins_get_job_url
from mr.roboto.jenkinsutil import jenkins_build_job
from mr.roboto.jenkinsutil import jenkins_remove_job
from mr.roboto.jenkinsutil import jenkins_job_external
from mr.roboto.buildout import PloneCoreBuildout

from mr.roboto.db import CorePackages
from mr.roboto.db import CorePackage
from mr.roboto.db import JenkinsJob
from mr.roboto.db import JenkinsJobs

from mr.roboto.events import NewPush

import transaction

import logging
import json
import uuid


logger = logging.getLogger('mr.roboto')

runCoreTests = Service(
    name='Run core tests',
    path='/run/corecommit',
    description="Run the core-dev buildout"
)

runPushTests = Service(
    name='Run push tests',
    path='/run/pullrequest',
    description="Run the core-dev buildout with a pull request"
)

createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description="Creates github post-commit hooks."
)

# CORE-DEV PYTHON VERSIONS

PYTHON_VERSIONS = ['2.6', '2.7']


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

    # Subscribers to a git push event
    request.registry.notify(NewPush(payload, request))

    # DB of jenkins jobs
    jenkins_jobs = JenkinsJobs(request.registry.settings['dm'])

    # We get the last commit id to have a reference
    last_commit = payload['commits'][0]['id']

    # Create jk job uuid
    jk_job_id = uuid.uuid4().hex

    organization = payload['repository']['organization']
    repo_name = payload['repository']['name']

    repo = organization + '/' + repo_name
    branch = payload['ref'].split('/')[-1]

    # Going to run the core-dev tests
    # Who is doing the push ??

    changeset = ""
    who = ""
    for commit in payload['commits']:
        who = commit['committer']['name'] + '<' + commit['committer']['email'] + '>'
        changeset += who + ' ' + commit['message'] + '\n'
        changeset += ' ' + commit['url'] + '\n\n'
        message = 'Commit trigger on ' + repo + ' ' + branch + ' ' + commit['id']
        add_log(request, who, message)

    # Params to send changes to jk
    params = {'plonechanges': changeset}

    # Define the callback url for jenkins
    url = request.registry.settings['callback_url'] + 'corecommit?jk_job_id=' + jk_job_id

    # In case is a push to buildout-coredev
    if repo == 'plone/buildout.coredev':
        for python_version in PYTHON_VERSIONS:
            job_name = 'plone-' + branch + '-python-' + python_version
            message = 'Start ' + job_name + ' Jenkins Job'

            jenkins_jobs[jk_job_id] = JenkinsJob('core', jk_job_id, repo=repo, branch=branch, who=who, jk_name=job_name, ref=last_commit)
            transaction.commit()

            # We create the JK job
            jenkins_core_job(request, job_name, url, payload=payload, params=params)
            add_log(request, who, message)

    # Look at DB which plone version needs to run tests
    core_jobs = list(request.registry.settings['db']['core_package'].find({'repo': repo, 'branch': branch}))

    # Run the core jobs related with this commit on jenkins
    for core_job in core_jobs:
        for python_version in PYTHON_VERSIONS:
            job_name = 'plone-' + core_job['plone_version'] + '-python-' + python_version
            message = 'Start ' + job_name + ' Jenkins Job'

            jenkins_jobs[jk_job_id] = JenkinsJob('core', jk_job_id, repo=repo, branch=branch, who=who, jk_name=job_name, ref=last_commit)
            transaction.commit()

            # We create the JK job
            jenkins_core_job(request, job_name, url, payload=payload, params=params)
            add_log(request, who, message)

    # Look at DB which PLIP jobs needs to run
    # We need to look if there is any PLIP job that needs to run tests
    plips = list(request.registry.settings['db']['plip'].find({'repo': [repo, branch]}))

    for plip in plips:
        # Run the JK jobs for each plip
        job_name = 'job-' + plip['description']
        message = 'Start ' + job_name + ' Jenkins Job'

        # We create the JK job
        jenkins_jobs[jk_job_id] = JenkinsJob('plip', jk_job_id, repo=repo, branch=branch, who=who, jk_name=job_name, ref=last_commit)
        transaction.commit()

        # We create the JK job
        jenkins_job_external(request, job_name, url, plip, payload=payload, params=params)
        add_log(request, who, message)


@runPushTests.post()
@validatetoken
def runFunctionPushTests(request):
    """
    When we are called by GH we want to run the jenkins core-dev builds
    """
    logger.info("Github sent us a pull request.")

    payload = json.loads(request.POST['payload'])
    repo_name = payload['repository']['full_name']
    pull_number = payload['number']
    pull_id = payload['pull_request']['id']
    package_name = payload['pull_request']['base']['repo']['name']
    target_branch = payload['pull_request']['base']['ref']
    pull_state = payload['pull_request']['state']

    logger.info("Found pull request %s on package %s"
                % (pull_number, repo_name))

    # Check local db for registered jobs
    pulls_db = request.registry.settings['pulls']
    pull_info = pulls_db.get(pull_id)

    pull_request_message = ""
    # Check state of pull request ('open' or 'closed')
    if pull_state == "open":
        if pull_info is None:
            # Consider this a new pull.
            # Check to see which coredev branches (if any) use this package
            # branch.
            logger.info("Checking coredev branches.")
            matched_branches = {}
            for branch in request.registry.settings('plone_versions'):
                core_buildout = PloneCoreBuildout(branch)
                if core_buildout.get_package_branch(package_name) == target_branch:
                    logger.info('Package branch is used by coredev %s' % branch)

                    # Create job
                    job_id = jenkins_create_pull_job(request, pull_id, branch)
                    if job_id:
                        matched_branches[branch] = job_id
            if not matched_branches:
                # Coredev doesn't use this package or branch. Ignore
                return

            pull_request_message += "Hi @%s. Thanks for your pull request!\n\n" % payload['sender']['login']
            branch_template = "\n* [Plone %s](%s)"
            branch_str = ''.join([branch_template % (a, jenkins_get_job_url(request, b)) for a, b in matched_branches.iteritems()])
            merge_test_str = "a merge test" if len(matched_branches) == 1 else "some merge tests"
            link_str = "link" if len(matched_branches) == 1 else "links"
            pull_request_message += "I've gone ahead and started %(merge_test_str)s for you: \n%(branch_str)s \n\nYou can check on the results at at the above %(link_str)s, or just wait a little while and I'll report them here.\n\n" % {'merge_test_str': merge_test_str, 'branch_str': branch_str, 'link_str': link_str}
            pull_request_message += "I'll also keep track of any future changes made to this pull request or to the Plone core build. If you'd like to manually run the merge tests at any point, you can do so via the %(link_str)s above." % {'link_str': link_str}

            # Add entry to db
            pull_info = pulls_db.set(pull_id, matched_branches.values(), [])

        # Check contributors
        logger.info("Getting github repository.")
        github = request.registry.settings['github']
        repository = github.get_repo(repo_name)
        pull = repository.get_pull(pull_number)
        committers = set([a.committer.login for a in pull.get_commits()])
        # Are there new committers?
        checked_committers = pull_info['seen_committers']
        for committer in committers:
            if committer not in checked_committers:
                logger.info("Checking contributor rights for %s." % committer)
                # Check all new committers for Plone contributor rights
                if not github.is_core_contributor(committer):
                    msg = """@%s, you've committed to this pull, but it looks like you haven't signed \
                            the Plone contributor agreement. You can find it at \
                            https://buildoutcoredev.readthedocs.org/en/latest/agreement.html\
                            . If you've already done so, let me know and I'll \
                            double-check.\n""" % committer
                    pull_request_message += msg

                checked_committers.append(committer)
        pulls_db.set(pull_id, pull_info['jenkins_jobs'], checked_committers)

        # Run jobs
        for job_id in pull_info['jenkins_jobs']:
            logger.info("Running job %s" % job_id)
            jenkins_build_job(request, job_id)

        # Add a comment to the pull request.
        print pull_request_message
        if pull_request_message:
            pull.create_issue_comment(pull_request_message)
    else:
        if pull_info is not None:
            # Consider this a merged pull
            # Remove job(s) from Jenkins
            for jenkins_identifier in pull_info['jenkins_jobs']:
                jenkins_remove_job(request, jenkins_identifier)
            # Remove entry from db.
            pulls_db.delete(pull_id)


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



