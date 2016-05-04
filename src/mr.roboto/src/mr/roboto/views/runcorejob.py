# -*- encoding: utf-8 -*-
from cornice import Service
from github import InputGitAuthor
from github import InputGitTreeElement
from mr.roboto import templates
from mr.roboto.buildout import get_sources_and_checkouts
from mr.roboto.events import CommitAndMissingCheckout
from mr.roboto.events import NewCoreDevPush
from mr.roboto.security import validate_github
from mr.roboto.subscriber import get_info_from_commit
from mr.roboto.utils import get_pickled_data

import datetime
import json
import logging


logger = logging.getLogger('mr.roboto')

runCoreTests = Service(
    name='Run core tests',
    path='/run/corecommit',
    description='Run the core-dev buildout'
)


class GMT1(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=1)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return 'Europe/Catalunya'


def get_user(data):
    if data['name'] == u'none':
        who = 'NoBody <nobody@plone.org>'
    else:
        who = '{0} <{1}>'.format(
            data['name'],
            data['email']
        )
    return who


def commit_to_coredev(
    request,
    payload,
    plone_version,
    changeset,
    changeset_long,
    timestamp
):
    logger.info('github commit LETS COMMIT ON COREDEV')
    gh = request.registry.settings['github']
    org = gh.get_organization('plone')
    repo = org.get_repo('buildout.coredev')
    head_ref = repo.get_git_ref('heads/{0}'.format(plone_version))
    latest_commit = repo.get_git_commit(head_ref.object.sha)
    base_tree = latest_commit.tree
    element = InputGitTreeElement(
        path='last_commit.txt',
        mode='100644',
        type='blob',
        content=changeset_long
    )
    new_tree = repo.create_git_tree([element], base_tree)
    new_user = InputGitAuthor(
        payload['pusher']['name'],
        payload['pusher']['email'],
        timestamp,
    )
    new_commit = repo.create_git_commit(
        '[fc] {0}'.format(changeset),
        new_tree,
        [latest_commit, ],
        new_user,
        new_user,
    )
    head_ref.edit(sha=new_commit.sha, force=False)


@runCoreTests.post()
@validate_github
def run_function_core_tests(request):
    """When we are called by GH we want to run the jenkins builds

    It's called for each push on the plone repo, so we look which tests needs
    to run for the given repository and branch:
    """
    # bail out early if it's just a github check
    payload = json.loads(request.POST['payload'])
    if 'ref' not in payload:
        return json.dumps({'message': 'pong'})

    # lots of variables
    changeset = ''
    changeset_long = ''
    commits_info = []
    timestamp = datetime.datetime.now(GMT1()).isoformat()
    fake = False
    skip = False
    source_or_checkout = False

    commit_data = None
    message = ''

    sources = get_pickled_data(request.registry.settings['sources_file'])
    checkouts = get_pickled_data(request.registry.settings['checkouts_file'])

    repo_name = payload['repository']['name']
    repo = payload['repository']['full_name']
    branch = payload['ref'].split('/')[-1]

    # who pushed the commits?
    who = get_user(payload['pusher'])

    # gather information about the commits. There are three special cases:
    # - fake: the commit was made by mr.roboto itself
    # - skip: the committer requested to skip CI for this commit,
    #   usually done by the release team to avoid flooding Jenkins
    # - sources_or_checkouts: either sources.cfg or checkouts.cfg has been
    #   changed (the data stored locally needs to be updated maybe)
    for commit in payload['commits']:
        # get the commit data structure
        commit_data = get_info_from_commit(commit)
        commits_info.append(commit_data)
        files = '\n'.join(commit_data['files'])

        if '[fc]' in commit_data['short_commit_msg']:
            fake = True
        if '[ci skip]' in commit_data['full_commit_msg']:
            skip = True
        if 'sources.cfg' in files or 'checkouts.cfg' in files:
            source_or_checkout = True

        # prepare a changeset text message
        data = {
            'push': payload,
            'commit': commit,
            'files': files,
            'diff': commit_data['diff'],
        }
        changeset += templates['github_commit.pt'](**data)
        changeset_long += templates['jenkins_changeset.pt'](**data)

        # get a timestamp for later usage when creating commits
        timestamp = commit['timestamp']

        message = 'Commit on {0} {1} {2}'.format(repo, branch, commit['id'])
        logger.info(message)

    if not fake and not skip:
        request.registry.notify(NewCoreDevPush(payload, request))

    # If it is a push to buildout.coredev,
    # update sources and checkouts and quit
    if repo == 'plone/buildout.coredev':
        logger.info('Commit to coredev - do nothing')
        if source_or_checkout:
            get_sources_and_checkouts(request)

        return json.dumps(
            {'message': 'Thanks! Commit to coredev, nothing to do'}
        )

    ##
    # It's not a commit to coredev repo
    ##

    # if it's a skip commit, log and done
    if skip:
        msg = 'Commit skipping CI - {0} - {1} do nothing'
        logger.info(msg.format(repo, branch))
        return json.dumps({'message': 'Thanks! Skipping CI'})

    # if the repo+branch are not in any plone version sources.cfg,
    # log and done
    elif (repo, branch) not in sources:
        # Error repo not sources
        msg = 'Commit not in sources - {0} - {1} do nothing'
        logger.info(msg.format(repo, branch))
        return json.dumps(
            {'message': 'Thanks! Commits done on a branch, nothing to do'}
        )

    ##
    # a commit on a branch that's part of a plone version
    ##
    affected_plone_versions = sources[(repo, branch)]
    for plone_version in affected_plone_versions:
        # if the repository is not on checkouts.cfg things could be broken
        # at a later point when it's added, warn about it!!
        if repo_name not in checkouts[plone_version]:
            request.registry.notify(
                CommitAndMissingCheckout(
                    who,
                    request,
                    repo,
                    branch,
                    plone_version,
                    payload['pusher']['email']  # duplicated, already on 'who'
                )
            )
        # commit to the plone version branch. This way jenkins will trigger a
        # build and will get the latest changes from the repository that
        # triggered this view
        commit_to_coredev(
            request,
            payload,
            plone_version,
            changeset,
            changeset_long,
            timestamp,
        )

    logger.info(message)
    return json.dumps(
        {'message': 'Thanks! Plone Jenkins CI will run tests'}
    )
