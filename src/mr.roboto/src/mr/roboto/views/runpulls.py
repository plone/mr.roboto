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


runPushTests = Service(
    name='Run push tests',
    path='/run/pullrequest',
    description="Run the core-dev buildout with a pull request"
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

    payload
    -------

    action
        string - The action that was performed. Can be one of “opened”, “closed”, “synchronize”, or “reopened”.
    number
        integer - The pull request number.
    pull_request
        object - The pull request itself.


    """
    logger.info("Github sent us a pull request.")

    payload = json.loads(request.POST['payload'])
    repo_name = payload['repository']['full_name']
    pull_number = payload['number']
    pull_id = payload['pull_request']['id']
    package_name = payload['pull_request']['base']['repo']['full_name']
    target_branch = payload['pull_request']['base']['ref']
    pull_state = payload['action']

    jenkins_jobs = JenkinsJobs(request.registry.settings['dm'])
    pushes = Pushes(request.registry.settings['dm'])

    logger.info("Found pull request %s on package %s"
                % (pull_number, repo_name))

    # Check local db for registered jobs
    if payload['pull_request']['user'] == u'none':
        # XXX correu ?
        who = "NoBody"
    else:
        who = "%s" % (payload['sender']['login'])


    pull_request_message = ""
    run_tests = False
    # Check state of pull request ('open' or 'closed')
    if pull_state == "opened":
        # Consider this a new pull.
        # A la base de dades
        pulls[pull_id] = PullRequest(repo=repo_name, branch=target_branch, who=who, ident=pull_id, payload=payload)

        pull_request_message += "Hi @%s. Thanks for your pull request!\n\n" % payload['sender']['login']
        branch_template = "\n* [Plone %s](%s)"
        branch_str = ''.join([branch_template % (a, jenkins_get_job_url(request, b)) for a, b in matched_branches.iteritems()])
        merge_test_str = "a merge test" if len(matched_branches) == 1 else "some merge tests"
        link_str = "link" if len(matched_branches) == 1 else "links"
        pull_request_message += "I've gone ahead and started %(merge_test_str)s for you: \n%(branch_str)s \n\nYou can check on the results at at the above %(link_str)s, or just wait a little while and I'll report them here.\n\n" % {'merge_test_str': merge_test_str, 'branch_str': branch_str, 'link_str': link_str}
        pull_request_message += "I'll also keep track of any future changes made to this pull request or to the Plone core build. If you'd like to manually run the merge tests at any point, you can do so via the %(link_str)s above." % {'link_str': link_str}

        run_tests = True

    if pull_state == "synchronize" or pull_state == "reopen":
        run_tests = True

    if pull_state == "closed":

        for jenkins_identifier in pull_info['jenkins_jobs']:
            jenkins_remove_job(request, jenkins_identifier)





    # Check contributors
    logger.info("Getting github repository.")
    github = request.registry.settings['github']
    repository = github.get_repo(repo_name)
    pull = repository.get_pull(pull_number)
    committers = set([a.committer.login for a in pull.get_commits()])
    # Are there new committers?
    checked_committers = "nobody"
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
            pulls[pull_id].seen_commiters.append(committer)

    if run_tests:

        core_jobs = list(request.registry.settings['db']['core_package'].find({'repo': package_name, 'branch': target_branch}))

        # Run the core jobs related with this commit on jenkins
        for core_job in core_jobs:
        # Add entry to db
        pull_info = pulls_db.set(pull_id, matched_branches.values(), [])





# {
#   "url": "https://api.github.com/repos/octocat/Hello-World/pulls/1",
#   "html_url": "https://github.com/octocat/Hello-World/pull/1",
#   "diff_url": "https://github.com/octocat/Hello-World/pulls/1.diff",
#   "patch_url": "https://github.com/octocat/Hello-World/pulls/1.patch",
#   "issue_url": "https://github.com/octocat/Hello-World/issue/1",
#   "statuses_url": "https://api.github.com/repos/octocat/Hello-World/statuses/6dcb09b5b57875f334f61aebed695e2e4193db5e",
#   "number": 1,
#   "state": "open",
#   "title": "new-feature",
#   "body": "Please pull these awesome changes",
#   "created_at": "2011-01-26T19:01:12Z",
#   "updated_at": "2011-01-26T19:01:12Z",
#   "closed_at": "2011-01-26T19:01:12Z",
#   "merged_at": "2011-01-26T19:01:12Z",
#   "head": {
#     "label": "new-topic",
#     "ref": "new-topic",
#     "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
#     "user": {
#       "login": "octocat",
#       "id": 1,
#       "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#       "gravatar_id": "somehexcode",
#       "url": "https://api.github.com/users/octocat"
#     },
#     "repo": {
#       "id": 1296269,
#       "owner": {
#         "login": "octocat",
#         "id": 1,
#         "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#         "gravatar_id": "somehexcode",
#         "url": "https://api.github.com/users/octocat"
#       },
#       "name": "Hello-World",
#       "full_name": "octocat/Hello-World",
#       "description": "This your first repo!",
#       "private": false,
#       "fork": false,
#       "url": "https://api.github.com/repos/octocat/Hello-World",
#       "html_url": "https://github.com/octocat/Hello-World",
#       "clone_url": "https://github.com/octocat/Hello-World.git",
#       "git_url": "git://github.com/octocat/Hello-World.git",
#       "ssh_url": "git@github.com:octocat/Hello-World.git",
#       "svn_url": "https://svn.github.com/octocat/Hello-World",
#       "mirror_url": "git://git.example.com/octocat/Hello-World",
#       "homepage": "https://github.com",
#       "language": null,
#       "forks": 9,
#       "forks_count": 9,
#       "watchers": 80,
#       "watchers_count": 80,
#       "size": 108,
#       "master_branch": "master",
#       "open_issues": 0,
#       "open_issues_count": 0,
#       "pushed_at": "2011-01-26T19:06:43Z",
#       "created_at": "2011-01-26T19:01:12Z",
#       "updated_at": "2011-01-26T19:14:43Z"
#     }
#   },
#   "base": {
#     "label": "master",
#     "ref": "master",
#     "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
#     "user": {
#       "login": "octocat",
#       "id": 1,
#       "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#       "gravatar_id": "somehexcode",
#       "url": "https://api.github.com/users/octocat"
#     },
#     "repo": {
#       "id": 1296269,
#       "owner": {
#         "login": "octocat",
#         "id": 1,
#         "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#         "gravatar_id": "somehexcode",
#         "url": "https://api.github.com/users/octocat"
#       },
#       "name": "Hello-World",
#       "full_name": "octocat/Hello-World",
#       "description": "This your first repo!",
#       "private": false,
#       "fork": false,
#       "url": "https://api.github.com/repos/octocat/Hello-World",
#       "html_url": "https://github.com/octocat/Hello-World",
#       "clone_url": "https://github.com/octocat/Hello-World.git",
#       "git_url": "git://github.com/octocat/Hello-World.git",
#       "ssh_url": "git@github.com:octocat/Hello-World.git",
#       "svn_url": "https://svn.github.com/octocat/Hello-World",
#       "mirror_url": "git://git.example.com/octocat/Hello-World",
#       "homepage": "https://github.com",
#       "language": null,
#       "forks": 9,
#       "forks_count": 9,
#       "watchers": 80,
#       "watchers_count": 80,
#       "size": 108,
#       "master_branch": "master",
#       "open_issues": 0,
#       "open_issues_count": 0,
#       "pushed_at": "2011-01-26T19:06:43Z",
#       "created_at": "2011-01-26T19:01:12Z",
#       "updated_at": "2011-01-26T19:14:43Z"
#     }
#   },
#   "_links": {
#     "self": {
#       "href": "https://api.github.com/repos/octocat/Hello-World/pulls/1"
#     },
#     "html": {
#       "href": "https://github.com/octocat/Hello-World/pull/1"
#     },
#     "comments": {
#       "href": "https://api.github.com/repos/octocat/Hello-World/issues/1/comments"
#     },
#     "review_comments": {
#       "href": "https://api.github.com/repos/octocat/Hello-World/pulls/1/comments"
#     },
#     "statuses": {
#       "href": "https://api.github.com/repos/octocat/Hello-World/statuses/6dcb09b5b57875f334f61aebed695e2e4193db5e"
#     }
#   },
#   "user": {
#     "login": "octocat",
#     "id": 1,
#     "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#     "gravatar_id": "somehexcode",
#     "url": "https://api.github.com/users/octocat"
#   },
#   "merge_commit_sha": "e5bd3914e2e596debea16f433f57875b5b90bcd6",
#   "merged": false,
#   "mergeable": true,
#   "merged_by": {
#     "login": "octocat",
#     "id": 1,
#     "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#     "gravatar_id": "somehexcode",
#     "url": "https://api.github.com/users/octocat"
#   },
#   "comments": 10,
#   "commits": 3,
#   "additions": 100,
#   "deletions": 3,
#   "changed_files": 5
# }

