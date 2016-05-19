# -*- encoding: utf-8 -*-
from mr.roboto import templates
from mr.roboto.events import CommitAndMissingCheckout
from mr.roboto.events import NewCoreDevPush
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from mr.roboto.utils import get_info_from_commit
from mr.roboto.utils import plone_versions_targeted
from mr.roboto.utils import shorten_pull_request_url
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
    'plone.jenkins_node',
    'plone.jenkins_server',
    'buildout.coredev',
    'ploneorg.core',
    'ploneorg.theme',
)

IGNORE_NO_AGREEMENT = (
    'icalendar',
)


def mail_missing_checkout(mailer, who, repo, branch, pv, email):
    msg = Message(
        subject='CHECKOUT ERROR {0} {1}'.format(repo, branch),
        sender='Jenkins Job FAIL <jenkins@plone.org>',
        recipients=[
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
    msg = 'Commit: send mail: coredev push to {0}'
    logger.info(msg.format(payload['repository']['name']))
    mail_to_cvs(payload, mailer)


@subscriber(CommitAndMissingCheckout)
def send_mail_on_missing_checkout(event):
    mailer = get_mailer(event.request)
    msg = 'Commit: send mail: coredev push without checkout of {0} by {1}'
    logger.info(msg.format(event.repo, event.who))
    mail_missing_checkout(
        mailer,
        event.who,
        event.repo,
        event.branch,
        event.pv,
        event.email)


class PullRequestSubscriber(object):

    def __init__(self, event):
        self.event = event
        self._github = None
        self._short_url = None
        self._pull_request = None
        self._repo_name = None
        self._repo_full_name = None
        self._g_pull = None
        self._commits_url = None

        self.run()

    @property
    def github(self):
        if self._github is None:
            self._github = self.event.request.registry.settings['github']
        return self._github

    @property
    def short_url(self):
        if self._short_url is None:
            self._short_url = shorten_pull_request_url(
                self.event.pull_request['html_url']
            )
        return self._short_url

    @property
    def pull_request(self):
        if self._pull_request is None:
            self._pull_request = self.event.pull_request
        return self._pull_request

    @property
    def repo_name(self):
        if self._repo_name is None:
            self._repo_name = self.pull_request['base']['repo']['name']
        return self._repo_name

    @property
    def repo_full_name(self):
        if self._repo_full_name is None:
            self._repo_full_name = \
                self.pull_request['base']['repo']['full_name']
        return self._repo_full_name

    @property
    def g_pull(self):
        """Get pygithub's pull request object and the last commit on it"""
        if self._g_pull is None:
            org = self.pull_request['base']['repo']['owner']['login']
            pull_number = int(self.pull_request['number'])

            g_org = self.github.get_organization(org)
            g_repo = g_org.get_repo(self.repo_name)
            self._g_pull = g_repo.get_pull(pull_number)
        return self._g_pull

    @property
    def commits_url(self):
        if self._commits_url is None:
            self._commits_url = self.pull_request['commits_url']
        return self._commits_url

    def run(self):
        raise NotImplemented

    def get_pull_request_last_commit(self):
        return self.g_pull.get_commits().reversed[0]

    def get_json_commits(self):
        """From a commits_url like
        https://github.com/plone/mr.roboto/pull/34/commits
        return the JSON provided by github, or None if something happens
        """
        try:
            commits_data = requests.get(self.commits_url)
        except RequestException:
            msg = 'PR {0}: error while trying to get its commits'
            logger.warn(msg.format(self.short_url))
            return

        try:
            json_data = commits_data.json()
        except ValueError:
            msg = 'PR {0}: error while getting its commits in JSON'
            logger.warn(msg.format(self.short_url))
            return

        return json_data

    def check_membership(self, json_data):
        plone_org = self.github.get_organization('plone')
        unknown = []
        members = []
        not_foundation = []
        for commit_info in json_data:
            for user in ('committer', 'author'):
                try:
                    login = commit_info[user]['login']
                except TypeError:
                    msg = 'PR {0}: commit does not have {1} user info'
                    logger.warn(msg.format(self.short_url, user))
                    unknown.append(
                        commit_info['commit']['author']['name']
                    )
                    continue

                # avoid looking up users twice
                if login in members or login in not_foundation:
                    continue

                g_user = self.github.get_user(login)
                if plone_org.has_in_members(g_user):
                    members.append(login)
                else:
                    not_foundation.append(login)

        return not_foundation, unknown


@subscriber(NewPullRequest, UpdatedPullRequest)
class ContributorsAgreementSigned(PullRequestSubscriber):

    def __init__(self, event):
        self.cla_url = 'http://docs.plone.org/develop/coredev/docs/contributors_agreement_explained.html'  # noqa
        self.github_help_setup_email_url = u'https://help.github.com/articles/adding-an-email-address-to-your-github-account/'  # noqa
        self.status_context = u'Plone Contributors Agreement verifier'

        super(ContributorsAgreementSigned, self).__init__(event)

    def run(self):
        """Check if all users involved in a pull request have signed the CLA"""
        if self.repo_name in IGNORE_NO_AGREEMENT:
            msg = 'PR {0}: whitelisted for contributors agreement'
            logger.info(msg.format(self.short_url))
            return

        json_data = self.get_json_commits()
        if not json_data:
            return

        not_foundation, unknown = self.check_membership(json_data)

        # get the pull request and last commit
        last_commit = self.get_pull_request_last_commit()

        status = u'success'
        status_message = u'All users have signed it'
        if not_foundation or unknown:
            status = u'error'
            status_message = u'Some users need to sign it'

        if not_foundation:
            # add a message mentioning all users that have not signed the
            # Contributors Agreement
            users = ' @'.join(not_foundation)
            msg = u'@{0} you need to sign Plone Contributor Agreement in ' \
                  u'order to merge this pull request.\n\n' \
                  u'Learn about the Plone Contributor Agreement: {1}'
            last_commit.create_comment(
                body=msg.format(users, self.cla_url),
            )

        if unknown:
            # add a message mentioning all unknown users,
            # but mention each of them only once
            users = ', '.join(set(unknown))
            msg = 'PR {0}: {1} missing contributors agreement'
            logger.info(msg.format(self.short_url, users))
            msg = u'{0} your emails are not known to GithHb and thus it is ' \
                  u'impossible to know if you have signed the Plone ' \
                  u'Contributor Agreement, which is required to merge this ' \
                  u'pull request.\n\n' \
                  u'Learn about the Plone Contributor Agreement: {1} ' \
                  u'How to add more emails to your GitHub account: {2} '
            last_commit.create_comment(
                body=msg.format(
                    users,
                    self.cla_url,
                    self.github_help_setup_email_url,
                )
            )

        last_commit.create_status(
            status,
            target_url=self.cla_url,
            description=status_message,
            context=self.status_context,
        )
        msg = 'PR {0}: Contributors Agreement report: {1}'
        logger.info(msg.format(self.short_url, status))


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnNoChangelogEntry(PullRequestSubscriber):

    def __init__(self, event):
        self.status_context = u'Changelog verifier'

        super(WarnNoChangelogEntry, self).__init__(event)

    def run(self):
        """If the pull request does not add a changelog entry, warn about it"""
        if self.repo_name in IGNORE_NO_CHANGELOG:
            msg = 'PR {0}: whitelisted for changelog entries'
            logger.info(msg.format(self.short_url))
            return

        status = u'success'
        description = u'Entry found'
        status_url = '{0}/missing-changelog'.format(
            self.event.request.registry.settings['roboto_url']
        )

        # check if the pull request modifies the changelog file
        diff_url = self.pull_request['diff_url']
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
        last_commit = self.get_pull_request_last_commit()

        last_commit.create_status(
            status,
            target_url=status_url,
            description=description,
            context=self.status_context,
        )

        msg = 'PR {0}: changelog entry: {1}'
        logger.info(msg.format(self.short_url, status))


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnTestsNeedToRun(PullRequestSubscriber):

    def __init__(self, event):
        self.jenkins_pr_job_url = \
            'http://jenkins.plone.org/job/pull-request-{0}/build?delay=0sec'
        self.status_context = 'Plone Jenkins CI - pull-request-{0}'

        super(WarnTestsNeedToRun, self).__init__(event)

    def run(self):
        """Create waiting status for all pull request jobs that should be run
        before a pull request can be safely merged
        """
        target_branch = self.pull_request['base']['ref']

        plone_versions = plone_versions_targeted(
            self.repo_full_name,
            target_branch,
            self.event.request
        )

        tracked_versions = \
            self.event.request.registry.settings['plone_versions']
        if self.repo_full_name == 'plone/buildout.coredev' and \
                target_branch in tracked_versions:
            plone_versions = (target_branch, )

        elif not plone_versions:
            msg = 'PR {0}: does not target any Plone version'
            logger.info(msg.format(self.short_url))
            return

        # get the pull request and last commit
        last_commit = self.get_pull_request_last_commit()

        for version in plone_versions:

            last_commit.create_status(
                u'pending',
                target_url=self.jenkins_pr_job_url.format(version),
                description='Please run the job, click here ----------->',
                context=self.status_context.format(version),
            )
            msg = 'PR {0}: created pending status for plone {1}'
            logger.info(
                msg.format(
                    self.short_url,
                    version,
                )
            )
