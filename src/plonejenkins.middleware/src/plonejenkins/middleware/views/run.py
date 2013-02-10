# -*- encoding: utf-8 -*-
from cornice import Service
from plonejenkins.middleware.security import validatetoken
from plonejenkins.middleware.jenkinsutil import jenkins_job
from plonejenkins.middleware.utils import add_log
from plonejenkins.middleware.buildout import PloneCoreBuildout


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


jenkins_jobs = ['plone-4.3', 'plone-4.2']

COREDEV_BRANCHES_TO_CHECK = ['4.2', '4.3']


@runCoreTests.post()
@validatetoken
def runFunctionCoreTests(request):
    """
    When we are called by GH we want to run the jenkins core-dev builds
    """
    payload = request.json_body

    # Going to run the core-dev tests
    for commit in payload['commits']:
        who = commit['name'] + '<' + commit['author'] + '>'
    message = 'Commit trigger on core-dev'
    add_log(request, who, message)

    # We need to run the core-dev tests
    jenkins = request.registry.settings['jenkins']
    # with a callback with the last commit hash
    # we should store all of them but right now is ok
    last_commit = payload['commits'][0]['id']
    url = request.registry.settings['callback_url'] + 'corecommit?commit_hash=' + last_commit

    for job in jenkins_jobs:
        jenkins_job(request, job, url)


@runPushTests.post()
@validatetoken
def runFunctionPushTests(request):
    """
    When we are called by GH we want to run the jenkins core-dev builds
    """
    add_log(request, "github", "Sent us a pull request.")

    payload = request.json_body
    repo_name = payload['repository']['full_name']
    pull_number = payload['number']
    pull_id = payload['pull_request']['id']
    package_name = payload['pull_request']['base']['repo']['name']
    target_branch = payload['pull_request']['base']['ref']

    add_log(request, "mr.roboto", "Getting github repository.")
    github = request.registry.settings['github']
    repository = github.get_repo(repo_name)
    pull = repository.get_pull(pull_number)

    pull_request_message = """Domo arigato."""

    # Check local db for registered jobs
    pulls_db = request.registry.settings['pulls']
    pull_info = pulls_db.get(pull_id)

    pull_request_message = ""

    # Check state of pull request ('open' or 'closed')
    if pull.state == "open":
        if pull_info is None:
            # Consider this a new pull.
            # Check to see which coredev branches (if any) use this package
            # branch.
            add_log(request, "mr.roboto", "Checking coredev branches.")
            jenkins_urls = []
            for branch in COREDEV_BRANCHES_TO_CHECK:
                core_buildout = PloneCoreBuildout(branch)
                if core_buildout.get_package_branch(package_name) == target_branch:
                    # TODO: Create job
                    # jenkins_urls.append(job_url)
                    pass
            if not jenkins_urls:
                # Coredev doesn't use this package or branch. Ignore
                return

            pull_request_message += "Thanks for your pull request!\n"
            # Add entry to db
            pull_info = pulls_db.set(pull_id, jenkins_urls, [])

        # Check contributors
        committers = dict([(a.committer.id, a.committer) for a in pull.get_commits()]).values()
        # Are there new committers?
        checked_committers = pull_info.seen_committers
        for committer in committers:
            if committer.login not in checked_committers:
                add_log(request, "mr.roboto", "Checking contributor rights for %s." % committer.login)
                # Check all new committers for Plone contributor rights
                if not github.is_core_contributor(committer.login):
                    msg = """@%s, it looks like you haven't signed \
                            the Plone contributor agreement. You can find it at \
                            https://buildoutcoredev.readthedocs.org/en/latest/agreement.html\
                            . If you've already done so, let me know and I'll \
                            double-check.\n""" % committer.login
                pull_request_message += msg

                checked_committers.append(committer.login)
        pulls_db.set(pull_id, pull_info.jenkins_url, checked_committers)

        # TODO: Run jobs

        # Add a comment to the pull request.
        print pull_request_message
        pull.create_issue_comment(pull_request_message)
    else:
        if pull_info is not None:
            # Consider this a merged pull
            # TODO: Remove job from Jenkins
            # TODO: Remove entry from db.

            pass




# Example payload Push

# {
#   "action": "synchronize",
#   "number": 4,
#   "pull_request": {
#     "_links": {
#       "comments": {
#         "href": "https://api.github.com/repos/esteele/Products.Archetypes/issues/4/comments"
#       },
#       "html": {
#         "href": "https://github.com/esteele/Products.Archetypes/pull/4"
#       },
#       "issue": {
#         "href": "https://api.github.com/repos/esteele/Products.Archetypes/issues/4"
#       },
#       "review_comments": {
#         "href": "https://api.github.com/repos/esteele/Products.Archetypes/pulls/4/comments"
#       },
#       "self": {
#         "href": "https://api.github.com/repos/esteele/Products.Archetypes/pulls/4"
#       }
#     },
#     "additions": 9,
#     "assignee": null,
#     "base": {
#       "label": "esteele:master",
#       "ref": "master",
#       "repo": {
#         "archive_url": "https://api.github.com/repos/esteele/Products.Archetypes/{archive_format}{/ref}",
#         "assignees_url": "https://api.github.com/repos/esteele/Products.Archetypes/assignees{/user}",
#         "blobs_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/blobs{/sha}",
#         "branches_url": "https://api.github.com/repos/esteele/Products.Archetypes/branches{/branch}",
#         "clone_url": "https://github.com/esteele/Products.Archetypes.git",
#         "collaborators_url": "https://api.github.com/repos/esteele/Products.Archetypes/collaborators{/collaborator}",
#         "comments_url": "https://api.github.com/repos/esteele/Products.Archetypes/comments{/number}",
#         "commits_url": "https://api.github.com/repos/esteele/Products.Archetypes/commits{/sha}",
#         "compare_url": "https://api.github.com/repos/esteele/Products.Archetypes/compare/{base}...{head}",
#         "contents_url": "https://api.github.com/repos/esteele/Products.Archetypes/contents/{+path}",
#         "contributors_url": "https://api.github.com/repos/esteele/Products.Archetypes/contributors",
#         "created_at": "2013-02-08T10:59:48Z",
#         "description": "None",
#         "downloads_url": "https://api.github.com/repos/esteele/Products.Archetypes/downloads",
#         "events_url": "https://api.github.com/repos/esteele/Products.Archetypes/events",
#         "fork": true,
#         "forks": 0,
#         "forks_count": 0,
#         "forks_url": "https://api.github.com/repos/esteele/Products.Archetypes/forks",
#         "full_name": "esteele/Products.Archetypes",
#         "git_commits_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/commits{/sha}",
#         "git_refs_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/refs{/sha}",
#         "git_tags_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/tags{/sha}",
#         "git_url": "git://github.com/esteele/Products.Archetypes.git",
#         "has_downloads": true,
#         "has_issues": false,
#         "has_wiki": false,
#         "homepage": "None",
#         "hooks_url": "https://api.github.com/repos/esteele/Products.Archetypes/hooks",
#         "html_url": "https://github.com/esteele/Products.Archetypes",
#         "id": 8092021,
#         "issue_comment_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/comments/{number}",
#         "issue_events_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/events{/number}",
#         "issues_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues{/number}",
#         "keys_url": "https://api.github.com/repos/esteele/Products.Archetypes/keys{/key_id}",
#         "labels_url": "https://api.github.com/repos/esteele/Products.Archetypes/labels{/name}",
#         "language": "Python",
#         "languages_url": "https://api.github.com/repos/esteele/Products.Archetypes/languages",
#         "merges_url": "https://api.github.com/repos/esteele/Products.Archetypes/merges",
#         "milestones_url": "https://api.github.com/repos/esteele/Products.Archetypes/milestones{/number}",
#         "mirror_url": null,
#         "name": "Products.Archetypes",
#         "notifications_url": "https://api.github.com/repos/esteele/Products.Archetypes/notifications{?since,all,participating}",
#         "open_issues": 1,
#         "open_issues_count": 1,
#         "owner": {
#           "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#           "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#           "followers_url": "https://api.github.com/users/esteele/followers",
#           "following_url": "https://api.github.com/users/esteele/following",
#           "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#           "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#           "id": 483999,
#           "login": "esteele",
#           "organizations_url": "https://api.github.com/users/esteele/orgs",
#           "received_events_url": "https://api.github.com/users/esteele/received_events",
#           "repos_url": "https://api.github.com/users/esteele/repos",
#           "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#           "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#           "type": "User",
#           "url": "https://api.github.com/users/esteele"
#         },
#         "private": false,
#         "pulls_url": "https://api.github.com/repos/esteele/Products.Archetypes/pulls{/number}",
#         "pushed_at": "2013-02-08T15:32:16Z",
#         "size": 200,
#         "ssh_url": "git@github.com:esteele/Products.Archetypes.git",
#         "stargazers_url": "https://api.github.com/repos/esteele/Products.Archetypes/stargazers",
#         "statuses_url": "https://api.github.com/repos/esteele/Products.Archetypes/statuses/{sha}",
#         "subscribers_url": "https://api.github.com/repos/esteele/Products.Archetypes/subscribers",
#         "subscription_url": "https://api.github.com/repos/esteele/Products.Archetypes/subscription",
#         "svn_url": "https://github.com/esteele/Products.Archetypes",
#         "tags_url": "https://api.github.com/repos/esteele/Products.Archetypes/tags{/tag}",
#         "teams_url": "https://api.github.com/repos/esteele/Products.Archetypes/teams",
#         "trees_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/trees{/sha}",
#         "updated_at": "2013-02-08T15:32:16Z",
#         "url": "https://api.github.com/repos/esteele/Products.Archetypes",
#         "watchers": 0,
#         "watchers_count": 0
#       },
#       "sha": "55de5f3e09315513d6c976f21ac634cf81ac1248",
#       "user": {
#         "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#         "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#         "followers_url": "https://api.github.com/users/esteele/followers",
#         "following_url": "https://api.github.com/users/esteele/following",
#         "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#         "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#         "id": 483999,
#         "login": "esteele",
#         "organizations_url": "https://api.github.com/users/esteele/orgs",
#         "received_events_url": "https://api.github.com/users/esteele/received_events",
#         "repos_url": "https://api.github.com/users/esteele/repos",
#         "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#         "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#         "type": "User",
#         "url": "https://api.github.com/users/esteele"
#       }
#     },
#     "body": "",
#     "changed_files": 1,
#     "closed_at": null,
#     "comments": 0,
#     "comments_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/4/comments",
#     "commits": 3,
#     "commits_url": "https://github.com/esteele/Products.Archetypes/pull/4/commits",
#     "created_at": "2013-02-08T14:40:56Z",
#     "deletions": 0,
#     "diff_url": "https://github.com/esteele/Products.Archetypes/pull/4.diff",
#     "head": {
#       "label": "esteele:push-test",
#       "ref": "push-test",
#       "repo": {
#         "archive_url": "https://api.github.com/repos/esteele/Products.Archetypes/{archive_format}{/ref}",
#         "assignees_url": "https://api.github.com/repos/esteele/Products.Archetypes/assignees{/user}",
#         "blobs_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/blobs{/sha}",
#         "branches_url": "https://api.github.com/repos/esteele/Products.Archetypes/branches{/branch}",
#         "clone_url": "https://github.com/esteele/Products.Archetypes.git",
#         "collaborators_url": "https://api.github.com/repos/esteele/Products.Archetypes/collaborators{/collaborator}",
#         "comments_url": "https://api.github.com/repos/esteele/Products.Archetypes/comments{/number}",
#         "commits_url": "https://api.github.com/repos/esteele/Products.Archetypes/commits{/sha}",
#         "compare_url": "https://api.github.com/repos/esteele/Products.Archetypes/compare/{base}...{head}",
#         "contents_url": "https://api.github.com/repos/esteele/Products.Archetypes/contents/{+path}",
#         "contributors_url": "https://api.github.com/repos/esteele/Products.Archetypes/contributors",
#         "created_at": "2013-02-08T10:59:48Z",
#         "description": "None",
#         "downloads_url": "https://api.github.com/repos/esteele/Products.Archetypes/downloads",
#         "events_url": "https://api.github.com/repos/esteele/Products.Archetypes/events",
#         "fork": true,
#         "forks": 0,
#         "forks_count": 0,
#         "forks_url": "https://api.github.com/repos/esteele/Products.Archetypes/forks",
#         "full_name": "esteele/Products.Archetypes",
#         "git_commits_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/commits{/sha}",
#         "git_refs_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/refs{/sha}",
#         "git_tags_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/tags{/sha}",
#         "git_url": "git://github.com/esteele/Products.Archetypes.git",
#         "has_downloads": true,
#         "has_issues": false,
#         "has_wiki": false,
#         "homepage": "None",
#         "hooks_url": "https://api.github.com/repos/esteele/Products.Archetypes/hooks",
#         "html_url": "https://github.com/esteele/Products.Archetypes",
#         "id": 8092021,
#         "issue_comment_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/comments/{number}",
#         "issue_events_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/events{/number}",
#         "issues_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues{/number}",
#         "keys_url": "https://api.github.com/repos/esteele/Products.Archetypes/keys{/key_id}",
#         "labels_url": "https://api.github.com/repos/esteele/Products.Archetypes/labels{/name}",
#         "language": "Python",
#         "languages_url": "https://api.github.com/repos/esteele/Products.Archetypes/languages",
#         "merges_url": "https://api.github.com/repos/esteele/Products.Archetypes/merges",
#         "milestones_url": "https://api.github.com/repos/esteele/Products.Archetypes/milestones{/number}",
#         "mirror_url": null,
#         "name": "Products.Archetypes",
#         "notifications_url": "https://api.github.com/repos/esteele/Products.Archetypes/notifications{?since,all,participating}",
#         "open_issues": 1,
#         "open_issues_count": 1,
#         "owner": {
#           "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#           "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#           "followers_url": "https://api.github.com/users/esteele/followers",
#           "following_url": "https://api.github.com/users/esteele/following",
#           "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#           "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#           "id": 483999,
#           "login": "esteele",
#           "organizations_url": "https://api.github.com/users/esteele/orgs",
#           "received_events_url": "https://api.github.com/users/esteele/received_events",
#           "repos_url": "https://api.github.com/users/esteele/repos",
#           "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#           "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#           "type": "User",
#           "url": "https://api.github.com/users/esteele"
#         },
#         "private": false,
#         "pulls_url": "https://api.github.com/repos/esteele/Products.Archetypes/pulls{/number}",
#         "pushed_at": "2013-02-08T15:32:16Z",
#         "size": 200,
#         "ssh_url": "git@github.com:esteele/Products.Archetypes.git",
#         "stargazers_url": "https://api.github.com/repos/esteele/Products.Archetypes/stargazers",
#         "statuses_url": "https://api.github.com/repos/esteele/Products.Archetypes/statuses/{sha}",
#         "subscribers_url": "https://api.github.com/repos/esteele/Products.Archetypes/subscribers",
#         "subscription_url": "https://api.github.com/repos/esteele/Products.Archetypes/subscription",
#         "svn_url": "https://github.com/esteele/Products.Archetypes",
#         "tags_url": "https://api.github.com/repos/esteele/Products.Archetypes/tags{/tag}",
#         "teams_url": "https://api.github.com/repos/esteele/Products.Archetypes/teams",
#         "trees_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/trees{/sha}",
#         "updated_at": "2013-02-08T15:32:16Z",
#         "url": "https://api.github.com/repos/esteele/Products.Archetypes",
#         "watchers": 0,
#         "watchers_count": 0
#       },
#       "sha": "c1e4b19df405c834c7532a098c16e89c23cebb97",
#       "user": {
#         "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#         "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#         "followers_url": "https://api.github.com/users/esteele/followers",
#         "following_url": "https://api.github.com/users/esteele/following",
#         "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#         "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#         "id": 483999,
#         "login": "esteele",
#         "organizations_url": "https://api.github.com/users/esteele/orgs",
#         "received_events_url": "https://api.github.com/users/esteele/received_events",
#         "repos_url": "https://api.github.com/users/esteele/repos",
#         "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#         "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#         "type": "User",
#         "url": "https://api.github.com/users/esteele"
#       }
#     },
#     "html_url": "https://github.com/esteele/Products.Archetypes/pull/4",
#     "id": 4056914,
#     "issue_url": "https://github.com/esteele/Products.Archetypes/issues/4",
#     "merge_commit_sha": "d4e5f736262659e7d41e97b2e8e9e08c09329023",
#     "mergeable": null,
#     "mergeable_state": "unknown",
#     "merged": false,
#     "merged_at": null,
#     "merged_by": null,
#     "milestone": null,
#     "number": 4,
#     "patch_url": "https://github.com/esteele/Products.Archetypes/pull/4.patch",
#     "review_comment_url": "/repos/esteele/Products.Archetypes/pulls/comments/{number}",
#     "review_comments": 0,
#     "review_comments_url": "https://github.com/esteele/Products.Archetypes/pull/4/comments",
#     "state": "open",
#     "title": "Test, please ignore.",
#     "updated_at": "2013-02-08T15:32:16Z",
#     "url": "https://api.github.com/repos/esteele/Products.Archetypes/pulls/4",
#     "user": {
#       "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#       "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#       "followers_url": "https://api.github.com/users/esteele/followers",
#       "following_url": "https://api.github.com/users/esteele/following",
#       "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#       "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#       "id": 483999,
#       "login": "esteele",
#       "organizations_url": "https://api.github.com/users/esteele/orgs",
#       "received_events_url": "https://api.github.com/users/esteele/received_events",
#       "repos_url": "https://api.github.com/users/esteele/repos",
#       "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#       "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#       "type": "User",
#       "url": "https://api.github.com/users/esteele"
#     }
#   },
#   "repository": {
#     "archive_url": "https://api.github.com/repos/esteele/Products.Archetypes/{archive_format}{/ref}",
#     "assignees_url": "https://api.github.com/repos/esteele/Products.Archetypes/assignees{/user}",
#     "blobs_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/blobs{/sha}",
#     "branches_url": "https://api.github.com/repos/esteele/Products.Archetypes/branches{/branch}",
#     "clone_url": "https://github.com/esteele/Products.Archetypes.git",
#     "collaborators_url": "https://api.github.com/repos/esteele/Products.Archetypes/collaborators{/collaborator}",
#     "comments_url": "https://api.github.com/repos/esteele/Products.Archetypes/comments{/number}",
#     "commits_url": "https://api.github.com/repos/esteele/Products.Archetypes/commits{/sha}",
#     "compare_url": "https://api.github.com/repos/esteele/Products.Archetypes/compare/{base}...{head}",
#     "contents_url": "https://api.github.com/repos/esteele/Products.Archetypes/contents/{+path}",
#     "contributors_url": "https://api.github.com/repos/esteele/Products.Archetypes/contributors",
#     "created_at": "2013-02-08T10:59:48Z",
#     "description": "None",
#     "downloads_url": "https://api.github.com/repos/esteele/Products.Archetypes/downloads",
#     "events_url": "https://api.github.com/repos/esteele/Products.Archetypes/events",
#     "fork": true,
#     "forks": 0,
#     "forks_count": 0,
#     "forks_url": "https://api.github.com/repos/esteele/Products.Archetypes/forks",
#     "full_name": "esteele/Products.Archetypes",
#     "git_commits_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/commits{/sha}",
#     "git_refs_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/refs{/sha}",
#     "git_tags_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/tags{/sha}",
#     "git_url": "git://github.com/esteele/Products.Archetypes.git",
#     "has_downloads": true,
#     "has_issues": false,
#     "has_wiki": false,
#     "homepage": "None",
#     "hooks_url": "https://api.github.com/repos/esteele/Products.Archetypes/hooks",
#     "html_url": "https://github.com/esteele/Products.Archetypes",
#     "id": 8092021,
#     "issue_comment_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/comments/{number}",
#     "issue_events_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues/events{/number}",
#     "issues_url": "https://api.github.com/repos/esteele/Products.Archetypes/issues{/number}",
#     "keys_url": "https://api.github.com/repos/esteele/Products.Archetypes/keys{/key_id}",
#     "labels_url": "https://api.github.com/repos/esteele/Products.Archetypes/labels{/name}",
#     "language": "Python",
#     "languages_url": "https://api.github.com/repos/esteele/Products.Archetypes/languages",
#     "merges_url": "https://api.github.com/repos/esteele/Products.Archetypes/merges",
#     "milestones_url": "https://api.github.com/repos/esteele/Products.Archetypes/milestones{/number}",
#     "mirror_url": null,
#     "name": "Products.Archetypes",
#     "notifications_url": "https://api.github.com/repos/esteele/Products.Archetypes/notifications{?since,all,participating}",
#     "open_issues": 1,
#     "open_issues_count": 1,
#     "owner": {
#       "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#       "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#       "followers_url": "https://api.github.com/users/esteele/followers",
#       "following_url": "https://api.github.com/users/esteele/following",
#       "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#       "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#       "id": 483999,
#       "login": "esteele",
#       "organizations_url": "https://api.github.com/users/esteele/orgs",
#       "received_events_url": "https://api.github.com/users/esteele/received_events",
#       "repos_url": "https://api.github.com/users/esteele/repos",
#       "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#       "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#       "type": "User",
#       "url": "https://api.github.com/users/esteele"
#     },
#     "private": false,
#     "pulls_url": "https://api.github.com/repos/esteele/Products.Archetypes/pulls{/number}",
#     "pushed_at": "2013-02-08T15:32:16Z",
#     "size": 200,
#     "ssh_url": "git@github.com:esteele/Products.Archetypes.git",
#     "stargazers_url": "https://api.github.com/repos/esteele/Products.Archetypes/stargazers",
#     "statuses_url": "https://api.github.com/repos/esteele/Products.Archetypes/statuses/{sha}",
#     "subscribers_url": "https://api.github.com/repos/esteele/Products.Archetypes/subscribers",
#     "subscription_url": "https://api.github.com/repos/esteele/Products.Archetypes/subscription",
#     "svn_url": "https://github.com/esteele/Products.Archetypes",
#     "tags_url": "https://api.github.com/repos/esteele/Products.Archetypes/tags{/tag}",
#     "teams_url": "https://api.github.com/repos/esteele/Products.Archetypes/teams",
#     "trees_url": "https://api.github.com/repos/esteele/Products.Archetypes/git/trees{/sha}",
#     "updated_at": "2013-02-08T15:32:16Z",
#     "url": "https://api.github.com/repos/esteele/Products.Archetypes",
#     "watchers": 0,
#     "watchers_count": 0
#   },
#   "sender": {
#     "avatar_url": "https://secure.gravatar.com/avatar/a25a9df6dcbd2c020989b6d479f4a00a?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
#     "events_url": "https://api.github.com/users/esteele/events{/privacy}",
#     "followers_url": "https://api.github.com/users/esteele/followers",
#     "following_url": "https://api.github.com/users/esteele/following",
#     "gists_url": "https://api.github.com/users/esteele/gists{/gist_id}",
#     "gravatar_id": "a25a9df6dcbd2c020989b6d479f4a00a",
#     "id": 483999,
#     "login": "esteele",
#     "organizations_url": "https://api.github.com/users/esteele/orgs",
#     "received_events_url": "https://api.github.com/users/esteele/received_events",
#     "repos_url": "https://api.github.com/users/esteele/repos",
#     "starred_url": "https://api.github.com/users/esteele/starred{/owner}{/repo}",
#     "subscriptions_url": "https://api.github.com/users/esteele/subscriptions",
#     "type": "User",
#     "url": "https://api.github.com/users/esteele"
#   }
# }


# Example payload

# {
# "before": "5aef35982fb2d34e9d9d4502f6ede1072793222d",
# "repository": {
# "url": "http://github.com/defunkt/github",
# "name": "github",
# "description": "You're lookin' at it.",
# "watchers": 5,
# "forks": 2,
# "private": 1,
# "owner": {
# "email": "chris@ozmm.org",
# "name": "defunkt"
# }
# },
# "commits": [
# {
# "id": "41a212ee83ca127e3c8cf465891ab7216a705f59",
# "url": "http://github.com/defunkt/github/commit/41a212ee83ca127e3c8cf465891ab7216a705f59",
# "author": {
# "email": "chris@ozmm.org",
# "name": "Chris Wanstrath"
# },
# "message": "okay i give in",
# "timestamp": "2008-02-15T14:57:17-08:00",
# "added": ["filepath.rb"]
# },
# {
# "id": "de8251ff97ee194a289832576287d6f8ad74e3d0",
# "url": "http://github.com/defunkt/github/commit/de8251ff97ee194a289832576287d6f8ad74e3d0",
# "author": {
# "email": "chris@ozmm.org",
# "name": "Chris Wanstrath"
# },
# "message": "update pricing a tad",
# "timestamp": "2008-02-15T14:36:34-08:00"
# }
# ],
# "after": "de8251ff97ee194a289832576287d6f8ad74e3d0",
# "ref": "refs/heads/master"
# }