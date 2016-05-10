# -*- encoding: utf-8 -*-
from mr.roboto import templates
from mr.roboto.events import CommitAndMissingCheckout
from mr.roboto.events import NewCoreDevPush
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from pyramid.events import subscriber
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from requests.exceptions import RequestException

import logging
import requests


logger = logging.getLogger('mr.roboto')


def get_info_from_commit(commit):
    diff = requests.get(commit['url'] + '.diff').content

    files = ['A {0}'.format(f) for f in commit['added']]
    files.extend('M {0}'.format(f) for f in commit['modified'])
    files.extend('D {0}'.format(f) for f in commit['removed'])

    short_commit_msg = commit['message'].split('\n')[0][:60]
    reply_to = '{0} <{1}>'.format(
        commit['committer']['name'],
        commit['committer']['email']
    )

    return {
        'diff': diff,
        'files': files,
        'short_commit_msg': short_commit_msg,
        'full_commit_msg': commit['message'],
        'reply_to': reply_to,
        'sha': commit['id']
    }


def mail_missing_checkout(mailer, who, repo, branch, pv, email):
    msg = Message(
        subject='CHECKOUT ERROR {0} {1}'.format(repo, branch),
        sender='Jenkins Job FAIL <jenkins@plone.org>',
        recipients=[  # XXX also to testbot
            'ramon.nb@gmail.com',
            'tisto@plone.org',
            email,
        ],
        body=templates['error_commit_checkout.pt'](
            who=who,
            repo=repo,
            branch=branch,
            pv=pv),
        )
    mailer.send_immediately(msg, fail_silently=False)


def mail_to_cvs(payload, mailer):
    # safeguard against github getting confused and sending us the entire
    # history
    if len(payload['commits']) > 40:
        return

    for commit in payload['commits']:

        commit_data = get_info_from_commit(commit)

        data = {
            'push': payload,
            'commit': commit,
            'files': '\n'.join(commit_data['files']),
            'diff': commit_data['diff'],
        }

        msg = Message(
            subject='{0}/{1}: {2}'.format(
                payload['repository']['name'],
                payload['ref'].split('/')[-1],
                commit_data['short_commit_msg']),
            sender='{0} <svn-changes@plone.org>'.format(
                commit['committer']['name']
            ),
            recipients=['plone-cvs@lists.sourceforge.net'],
            body=templates['commit_email.pt'](**data),
            extra_headers={'Reply-To': commit_data['reply_to']}
        )

        mailer.send_immediately(msg, fail_silently=False)


@subscriber(NewCoreDevPush)
def send_mail_on_coredev(event):
    mailer = get_mailer(event.request)
    payload = event.payload
    msg = 'Sending mail due to a coredev push to {0}'
    logger.info(msg.format(payload['repository']['name']))
    mail_to_cvs(payload, mailer)


@subscriber(CommitAndMissingCheckout)
def send_mail_on_missing_checkout(event):
    mailer = get_mailer(event.request)
    msg = 'Sending mail due to a coredev push and no checkout of {0} by {1}'
    logger.info(msg.format(event.repo, event.who))
    mail_missing_checkout(
        mailer,
        event.who,
        event.repo,
        event.branch,
        event.pv,
        event.email)


@subscriber(NewPullRequest)
@subscriber(UpdatedPullRequest)
def have_signed_contributors_agreement(event):
    """Check if all users involved in a pull request have signed the CLA

    :param event: NewPullRequest or UpdatePullRequest object
    :return: None
    """
    # tons of data
    github = event.request.registry.settings['github']
    pull_request = event.pull_request
    pull_request_url = pull_request['html_url']
    org = pull_request['base']['repo']['owner']['login']
    repo = pull_request['base']['repo']['name']
    pull_number = int(pull_request['number'])
    plone_org = github.get_organization('plone')
    cla_url = 'http://docs.plone.org/develop/coredev/docs/contributors_agreement_explained.html'  # noqa

    try:
        commits_data = requests.get(pull_request['commits_url'])
    except RequestException:
        msg = 'Error while trying to get commits from pull request {0}'
        logger.warn(msg.format(pull_request_url))
        return

    try:
        json_data = commits_data.json()
    except ValueError:
        msg = 'Error while getting JSON data from pull request {0}'
        logger.warn(msg.format(pull_request_url))
        return

    members = []
    not_foundation_members = []
    for commit_info in json_data:
        for user in ('committer', 'author'):
            try:
                login = commit_info['commit'][user]['login']
            except KeyError:
                msg = 'Commit on pull request {0} does not have {1} user info'
                logger.warn(msg.format(pull_request_url, user))
                continue

            # avoid looking up users twice
            if login in members or login in not_foundation_members:
                continue

            g_user = github.get_user(login)
            if plone_org.has_in_members(g_user):
                members.append(login)
            else:
                not_foundation_members.append(login)

    # get the pull request
    if org == u'plone':
        g_org = plone_org
    else:
        g_org = github.get_organization(org)

    g_repo = g_org.get_repo(repo)
    g_pull = g_repo.get_pull(pull_number)

    # get last commit
    last_commit = g_pull.get_commits().reversed[0]

    status = u'success'
    status_message = u'All users have signed it'
    if not_foundation_members:
        status = u'error'
        status_message = u'Some users need to sign it'

        # add a message mentioning all users that have not signed the
        # Contributors Agreement
        users = ' @'.join(not_foundation_members)
        msg = u'@{0} you need to sign Plone Contributor Agreement in order ' \
              u'to merge this pull request.' \
              u'' \
              u'Learn about the Plone Contributor Agreement: {1}'
        last_commit.create_comment(body=msg.format(users, cla_url))

    last_commit.create_status(
        status,
        target_url=cla_url,
        description=status_message,
        context='Plone Contributors Agreement verifier',
    )
    msg = 'Pull request {0} Contributors Agreement report: {1}'
    logger.info(msg.format(pull_request_url, status))
