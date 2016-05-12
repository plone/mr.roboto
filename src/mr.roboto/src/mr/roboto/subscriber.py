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
from unidiff import PatchSet

import logging
import re
import requests


logger = logging.getLogger('mr.roboto')

VALID_CHANGELOG_FILES = re.compile(r'(CHANGES|HISTORY).(txt|rst)$')

IGNORE_NO_CHANGELOG = (
    'documentation',
    'mr.roboto',
    'jenkins.plone.org',
)

IGNORE_NO_AGREEMENT = (
    'icalendar',
)


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


def get_github_pull_request(github, pull_request_data):
    """Get pygithub's pull request object and the last commit on it"""
    repo_data = pull_request_data['base']['repo']
    org = repo_data['owner']['login']
    repo = repo_data['name']
    pull_number = int(pull_request_data['number'])

    g_org = github.get_organization(org)

    g_repo = g_org.get_repo(repo)
    g_pull = g_repo.get_pull(pull_number)
    last_commit = g_pull.get_commits().reversed[0]
    return g_pull, last_commit


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
    repo = pull_request['base']['repo']['name']
    plone_org = github.get_organization('plone')
    cla_url = 'http://docs.plone.org/develop/coredev/docs/contributors_agreement_explained.html'  # noqa

    if repo in IGNORE_NO_AGREEMENT:
        msg = 'Repo {0} whitelisted for contributors agreement'
        logger.info(msg.format(pull_request_url))
        return

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
    unknown_users = []
    for commit_info in json_data:
        for user in ('committer', 'author'):
            try:
                login = commit_info[user]['login']
            except TypeError:
                msg = 'Commit on pull request {0} does not have {1} user info'
                logger.warn(msg.format(pull_request_url, user))
                unknown_users.append(
                    commit_info['commit']['author']['name']
                )
                continue

            # avoid looking up users twice
            if login in members or login in not_foundation_members:
                continue

            g_user = github.get_user(login)
            if plone_org.has_in_members(g_user):
                members.append(login)
            else:
                not_foundation_members.append(login)

    # get the pull request and last commit
    g_pull, last_commit = get_github_pull_request(github, pull_request)

    status = u'success'
    status_message = u'All users have signed it'
    if not_foundation_members or unknown_users:
        status = u'error'
        status_message = u'Some users need to sign it'

    if not_foundation_members:
        # add a message mentioning all users that have not signed the
        # Contributors Agreement
        users = ' @'.join(not_foundation_members)
        msg = u'@{0} you need to sign Plone Contributor Agreement in order ' \
              u'to merge this pull request.' \
              u'' \
              u'Learn about the Plone Contributor Agreement: {1}'
        last_commit.create_comment(body=msg.format(users, cla_url))

    if unknown_users:
        # add a message mentioning all unknown users
        users = ', '.join(unknown_users)
        msg = u'{0} your emails are not known to GithHb and thus it is ' \
              u'impossible to know if you have signed the Plone Contributor ' \
              u'Agreement, which is required to merge this pull request.' \
              u'' \
              u'Learn about the Plone Contributor Agreement: {1} ' \
              u'How to add more emails to your GitHub account: {2} '
        last_commit.create_comment(
            body=msg.format(
                users,
                cla_url,
                u'https://help.github.com/articles/adding-an-email-address-to-your-github-account/'  # noqa
            )
        )

    last_commit.create_status(
        status,
        target_url=cla_url,
        description=status_message,
        context='Plone Contributors Agreement verifier',
    )
    msg = 'Pull request {0} Contributors Agreement report: {1}'
    logger.info(msg.format(pull_request_url, status))


@subscriber(NewPullRequest)
@subscriber(UpdatedPullRequest)
def warn_if_no_changelog_entry(event):
    """If the pull request does not add a changelog entry, warn about it"""
    github = event.request.registry.settings['github']
    pull_request = event.pull_request
    pull_request_url = pull_request['html_url']
    repo_name = pull_request['base']['repo']['name']

    if repo_name in IGNORE_NO_CHANGELOG:
        pull_request_url = pull_request['html_url']
        msg = 'Pull request {0} whitelisted for changelog entries'
        logger.info(msg.format(pull_request_url))
        return

    status = u'success'
    description = u'Entry found'
    status_url = '{0}/missing-changelog'.format(
        event.request.registry.settings['roboto_url']
    )

    # check if the pull request modifies the changelog file
    diff_url = pull_request['diff_url']
    # temporal workaround (not verifying SSL certificates) until
    # https://github.com/plone/jenkins.plone.org/issues/170 is fixed
    diff_data = requests.get(diff_url, verify=False)
    patch_data = PatchSet(
        diff_data.content.splitlines(),
        encoding=diff_data.encoding,
    )

    for diff_file in patch_data:
        if VALID_CHANGELOG_FILES.search(diff_file.path):
            break
    else:
        status = u'error'
        description = u'No entry found!'

    # get the pull request and last commit
    g_pull, last_commit = get_github_pull_request(github, pull_request)

    last_commit.create_status(
        status,
        target_url=status_url,
        description=description,
        context=u'Changelog verifier',
    )

    msg = 'Pull request {0} changelog entry: {1}'
    logger.info(msg.format(pull_request_url, status))
