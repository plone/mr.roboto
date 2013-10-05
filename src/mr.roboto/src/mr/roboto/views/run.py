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

import transaction

import logging
import json
import uuid


logger = logging.getLogger('mr.roboto')


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

OLD_PYTHON_VERSIONS = ['2.6', '2.7']
PYTHON_VERSIONS = ['2.7']


def add_log(request, who, message):
    logger.info(who + " " + message)


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



