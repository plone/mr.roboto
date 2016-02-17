# -*- encoding: utf-8 -*-
from cornice import Service
from github import InputGitAuthor
from github import InputGitTreeElement
from mr.roboto import templates
from mr.roboto.events import CommitAndMissingCheckout
from mr.roboto.events import NewCoreDevPush
from mr.roboto.security import validate_github
from mr.roboto.subscriber import get_info_from_commit
from mr.roboto.views.runhooks import get_sources_and_checkouts

import datetime
import json
import logging
import pickle


logger = logging.getLogger('mr.roboto')

runCoreTests = Service(
    name='Run core tests',
    path='/run/corecommit',
    description='Run the core-dev buildout'
)


def add_log(request, who, message):
    logger.info(who + ' ' + message)


class GMT1(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=1)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return 'Europe/Catalunya'


@runCoreTests.post()
@validate_github
def run_function_core_tests(request):
    """When we are called by GH we want to run the jenkins builds

    It's called for each push on the plone repo, so we look which tests needs
    to be runned for this repo:

    * Core Dev : it's on sources
    * PLIP : it's added as specific PLIP
    * Package : it's added as specific package
    """
    payload = json.loads(request.POST['payload'])

    sources_file = request.registry.settings['sources_file']
    checkouts_file = request.registry.settings['checkouts_file']

    sources = pickle.loads(open(sources_file, 'r').read())
    checkouts = pickle.loads(open(checkouts_file, 'r').read())

    # General Vars we need
    organization = payload['repository']['full_name'].split('/')[0]
    repo_name = payload['repository']['name']

    repo = organization + '/' + repo_name
    if 'ref' not in payload:
        # Its not a commit, just a github check
        return
    branch = payload['ref'].split('/')[-1]

    # Going to run the core-dev tests
    # Who is doing the push ??

    if payload['pusher']['name'] == u'none':
        who = 'NoBody <nobody@plone.org>'
    else:
        who = '{0} <{1}>'.format(
            payload['pusher']['name'],
            payload['pusher']['email']
        )
    changeset = ''
    changeset_long = ''
    commits_info = []
    timestamp = datetime.datetime.now(GMT1()).isoformat()
    fake = False
    skip = False
    source_or_checkout = False

    commit_data = None
    message = ''

    for commit in payload['commits']:
        # get the commit data structure
        commit_data = get_info_from_commit(commit)
        commits_info.append(commit_data)
        if '[fc]' in commit_data['short_commit_msg']:
            fake = True
        if '[ci skip]' in commit_data['full_commit_msg']:
            skip = True
        # prepare a changeset text message
        data = {
            'push': payload,
            'commit': commit,
            'files': '\n'.join(commit_data['files']),
            'diff': commit_data['diff'],
        }
        if 'sources.cfg' in data['files'] or 'checkouts.cfg' in data['files']:
            source_or_checkout = True
        changeset += templates['github_commit.pt'](**data)
        changeset_long += templates['jenkins_changeset.pt'](**data)
        timestamp = commit['timestamp']
        # For logging
        message = 'Commit on ' + repo + ' ' + branch + ' ' + commit['id']
        add_log(request, commit_data['reply_to'], message)

    if not fake and not skip:
        request.registry.notify(NewCoreDevPush(payload, request))

    # In case is a push to buildout-coredev
    if repo == 'plone/buildout.coredev' and commit_data:
        # don't do anything
        add_log(
            request,
            commit_data['reply_to'],
            'Commit to coredev - do nothing'
        )
        if source_or_checkout:
            get_sources_and_checkouts(request)

    else:
        # It's not a commit to coredev repo
        # Look at DB which plone version needs to run tests
        versions_to_commit = []
        if not skip and (repo, branch) in sources:
            versions_to_commit = sources[(repo, branch)]
            for pv in versions_to_commit:
                if repo_name not in checkouts[pv]:
                    request.registry.notify(
                        CommitAndMissingCheckout(
                            who,
                            request,
                            repo,
                            branch,
                            pv,
                            payload['pusher']['email']
                        )
                    )
        elif skip:
            msg = 'Commit skipping CI - %s/%s do nothing'
            add_log(request, who, msg.format(repo, branch))
        else:
            # Error repo not sources
            msg = 'Commit not in sources - %s/%s do nothing'
            add_log(request, who, msg.format(repo, branch))

        for pv in versions_to_commit:
            # commit to the branch
            add_log(request, 'github commit', 'LETS COMMIT ON COREDEV')
            gh = request.registry.settings['github']
            org = gh.get_organization('plone')
            repo = org.get_repo('buildout.coredev')
            head_ref = repo.get_git_ref('heads/{0}'.format(pv))
            latest_commit = repo.get_git_commit(head_ref.object.sha)
            base_tree = latest_commit.tree
            element = InputGitTreeElement(
                path='last_commit.txt',
                mode='100644',
                type='blob',
                content=changeset_long
            )
            new_tree = repo.create_git_tree([element], base_tree)
            new_user = InputGitAuthor(payload['pusher']['name'],
                                      payload['pusher']['email'], timestamp)
            new_commit = repo.create_git_commit('[fc] ' + changeset, new_tree,
                                                [latest_commit], new_user,
                                                new_user)
            head_ref.edit(sha=new_commit.sha, force=False)

        add_log(request, who, message)
