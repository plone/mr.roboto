# -*- encoding: utf-8 -*-
from datetime import datetime
from github import GithubException
from github import InputGitAuthor
from github import InputGitTreeElement
from mr.roboto import templates
from mr.roboto.events import CommentOnPullRequest
from mr.roboto.events import CommitAndMissingCheckout
from mr.roboto.events import MergedPullRequest
from mr.roboto.events import NewCoreDevPush
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from mr.roboto.utils import get_info_from_commit
from mr.roboto.utils import get_pickled_data
from mr.roboto.utils import plone_versions_targeted
from mr.roboto.utils import shorten_comment_url
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

VALID_CHANGELOG_FILES = re.compile(r'(CHANGES|HISTORY|CHANGELOG).(txt|rst|md)$')

IGNORE_NO_CHANGELOG = (
    'documentation',
    'mr.roboto',
    'jenkins.plone.org',
    'plone.jenkins_node',
    'plone.jenkins_server',
    'buildout.coredev',
    'ploneorg.core',
    'ploneorg.theme',
    'planet.plone.org',
    'training',
)

IGNORE_NO_AGREEMENT = ('icalendar', 'planet.plone.org', 'documentation', 'training')

IGNORE_USER_NO_AGREEMENT = ('web-flow',)

IGNORE_NO_TEST_NEEDED = ('plone.releaser',)


def mail_missing_checkout(mailer, who, repo, branch, pv, email):
    msg = Message(
        subject=f'POSSIBLE CHECKOUT ERROR {repo} {branch}',
        sender='Jenkins Job FAIL <jenkins@plone.org>',
        recipients=['ramon.nb@gmail.com', 'tisto@plone.org', email],
        body=templates['error_commit_checkout.pt'](
            who=who, repo=repo, branch=branch, pv=pv
        ),
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

        repo_name = payload['repository']['name']
        branch = payload['ref'].split('/')[-1]
        commit_msg = commit_data['short_commit_msg']
        msg = Message(
            subject=f'{repo_name}/{branch}: {commit_msg}',
            sender=f'{commit["committer"]["name"]} <svn-changes@plone.org>',
            recipients=['plone-cvs@lists.sourceforge.net'],
            body=templates['commit_email.pt'](**data),
            extra_headers={'Reply-To': commit_data['reply_to']},
        )

        mailer.send_immediately(msg, fail_silently=False)


@subscriber(NewCoreDevPush)
def send_mail_on_coredev(event):
    mailer = get_mailer(event.request)
    payload = event.payload
    repo_name = payload['repository']['name']
    logger.info(f'Commit: send mail: coredev push to {repo_name}')
    mail_to_cvs(payload, mailer)


@subscriber(CommitAndMissingCheckout)
def send_mail_on_missing_checkout(event):
    mailer = get_mailer(event.request)
    logger.info(
        f'Commit: send mail: coredev push without checkout of '
        f'{event.repo} by {event.who}'
    )
    mail_missing_checkout(
        mailer, event.who, event.repo, event.branch, event.pv, event.email
    )


class PullRequestSubscriber(object):
    def __init__(self, event):
        self.event = event
        self._github = None
        self._short_url = None
        self._pull_request = None
        self._repo_name = None
        self._repo_full_name = None
        self._g_pull = None
        self._g_issue = None
        self._commits_url = None
        self._target_branch = None

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
            self._repo_full_name = self.pull_request['base']['repo']['full_name']
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
    def g_issue(self):
        """Get pygithub's issue for the current pull request"""
        if self._g_issue is None:
            org = self.pull_request['base']['repo']['owner']['login']
            pull_number = int(self.pull_request['number'])

            g_org = self.github.get_organization(org)
            g_repo = g_org.get_repo(self.repo_name)
            self._g_issue = g_repo.get_issue(pull_number)
        return self._g_issue

    @property
    def commits_url(self):
        if self._commits_url is None:
            self._commits_url = self.pull_request['commits_url']
        return self._commits_url

    @property
    def target_branch(self):
        if self._target_branch is None:
            self._target_branch = self.pull_request['base']['ref']
        return self._target_branch

    def run(self):
        raise NotImplementedError

    def log(self, msg, level='info'):
        if level == 'warn':
            logger.warning(f'PR {self.short_url}: {msg}')
            return
        logger.info(f'PR {self.short_url}: {msg}')

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
            self.log('error while trying to get its commits')
            return

        try:
            json_data = commits_data.json()
        except ValueError:
            self.log('error while getting its commits in JSON')
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
                    self.log(f'commit does not have {user} user info')
                    unknown.append(commit_info['commit']['author']['name'])
                    continue

                if login in IGNORE_USER_NO_AGREEMENT:
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
            self.log('whitelisted for contributors agreement')
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
            msg = (
                f'@{users} you need to sign the Plone Contributor '
                f'Agreement in order to merge this pull request. \n\n'
                f'Learn about the Plone Contributor Agreement: {self.cla_url}'
            )
            self.g_issue.create_comment(body=msg)

        if unknown:
            # add a message mentioning all unknown users,
            # but mention each of them only once
            users = ', '.join(set(unknown))
            self.log(f'{users} missing contributors agreement')
            msg = (
                f'{users} your emails are not known to GitHub and thus it '
                f'is impossible to know if you have signed the Plone '
                f'Contributor Agreement, which is required to merge this '
                f'pull request.\n\n'
                f'Learn about the Plone Contributor Agreement: {self.cla_url} '
                f'How to add more emails to your GitHub account: '
                f'{self.github_help_setup_email_url} '
            )
            self.g_issue.create_comment(body=msg)

        last_commit.create_status(
            status,
            target_url=self.cla_url,
            description=status_message,
            context=self.status_context,
        )
        self.log(f'Contributors Agreement report: {status}')


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnNoChangelogEntry(PullRequestSubscriber):
    def __init__(self, event):
        self.status_context = u'Changelog verifier'

        super(WarnNoChangelogEntry, self).__init__(event)

    def run(self):
        """If the pull request does not add a changelog entry, warn about it"""
        if self.repo_name in IGNORE_NO_CHANGELOG:
            self.log('whitelisted for changelog entries')
            return

        status = u'success'
        description = u'Entry found'
        roboto_url = self.event.request.registry.settings['roboto_url']

        # check if the pull request modifies the changelog file
        diff_url = self.pull_request['diff_url']
        diff_data = requests.get(diff_url)
        patch_data = PatchSet(
            diff_data.content.splitlines(), encoding=diff_data.encoding
        )

        for diff_file in patch_data:
            if VALID_CHANGELOG_FILES.search(diff_file.path):
                break
            if diff_file.path.startswith('news/'):
                # towncrier news snippet
                break
        else:
            status = u'error'
            description = u'No entry found!'

        # get the pull request and last commit
        last_commit = self.get_pull_request_last_commit()

        last_commit.create_status(
            status,
            target_url=f'{roboto_url}/missing-changelog',
            description=description,
            context=self.status_context,
        )

        self.log(f'changelog entry: {status}')


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnTestsNeedToRun(PullRequestSubscriber):
    def __init__(self, event):
        self.jenkins_pr_job_url = (
            'http://jenkins.plone.org/job/pull-request-{0}/build?delay=0sec'
        )
        self.status_context = 'Plone Jenkins CI - pull-request-{0}'

        super(WarnTestsNeedToRun, self).__init__(event)

    def run(self):
        """Create waiting status for all pull request jobs that should be run
        before a pull request can be safely merged
        """
        plone_versions = self._plone_versions_targeted()

        # get the pull request last commit
        last_commit = self.get_pull_request_last_commit()

        for version in plone_versions:
            self._create_commit_status(last_commit, version)
            self.log(f'created pending status for plone {version}')

    def _plone_versions_targeted(self):
        if self.repo_name in IGNORE_NO_TEST_NEEDED:
            self.log('skip adding test warnings, repo whitelisted')
            return []

        target_branch = self.pull_request['base']['ref']

        plone_versions = plone_versions_targeted(
            self.repo_full_name, target_branch, self.event.request
        )

        tracked_versions = self.event.request.registry.settings['plone_versions']
        if (
            self.repo_full_name == 'plone/buildout.coredev'
            and target_branch in tracked_versions
        ):
            plone_versions = (target_branch,)

        elif not plone_versions:
            self.log('does not target any Plone version')
            return []

        return plone_versions

    def _create_commit_status(self, commit, version):
        commit.create_status(
            u'pending',
            target_url=self.jenkins_pr_job_url.format(version),
            description='Please run the job, click here --->',
            context=self.status_context.format(version),
        )


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnPy3TestsNeedToRun(WarnTestsNeedToRun):
    def run(self):
        """Create waiting status for pull requests that target plone 5.2 on
        python 3
        """
        self.jenkins_pr_job_url = (
            'http://jenkins.plone.org/job/pull-request-5.2-{0}/build?delay=0sec'
        )
        self.status_context = 'Plone Jenkins CI - pull-request-5.2-{0}'

        plone_versions = self._plone_versions_targeted()

        if '5.2' not in plone_versions:
            self.log('does not target Plone 5.2, no py3 pull request job needed')
            return

        py3_tracked_versions = self.event.request.registry.settings['py3_versions']

        # get the pull request and last commit
        last_commit = self.get_pull_request_last_commit()

        for py_version in py3_tracked_versions:
            self._create_commit_status(last_commit, py_version)
            self.log(f'created pending status for plone 5.2 on python {py_version}')


@subscriber(NewPullRequest, UpdatedPullRequest)
class TriggerDependenciesJob(PullRequestSubscriber):
    def run(self):
        """Trigger the dependencies jenkins job"""
        branch = self.pull_request['head']['ref']

        if not self.is_core_package():
            base_branch = self.pull_request['base']['ref']
            key = f'{self.repo_full_name}/{base_branch}'
            self.log(f'No dependencies jenkins job run on a non-core package {key}')
            return

        settings = self.event.request.registry.settings
        jenkins_url = settings['jenkins_url']

        requests.post(
            f'{jenkins_url}/job/qa-pkg-dependencies/buildWithParameters',
            data={'PACKAGE_NAME': self.repo_name, 'BRANCH': branch},
            auth=(settings['jenkins_user_id'], settings['jenkins_user_token']),
        )

        self.log(
            f'Trigger dependencies jenkins job for ' f'pull request {self.short_url}'
        )

    def is_core_package(self):
        base_branch = self.pull_request['base']['ref']
        return plone_versions_targeted(
            self.repo_full_name, base_branch, self.event.request
        )


@subscriber(MergedPullRequest)
class UpdateCoredevCheckouts(PullRequestSubscriber):
    def run(self):
        """Add package that got a pull request merged into checkouts.cfg

        - only for packages that are part of Plone coredev.
        - on all Plone coredev versions that track the branch that was
        targeted by the pull request
        """
        # pull requests on buildout.coredev itself do not need any extra work
        if self.repo_full_name == 'plone/buildout.coredev':
            return

        plone_versions = plone_versions_targeted(
            self.repo_full_name, self.target_branch, self.event.request
        )
        if not plone_versions:
            self.log(
                f'no plone coredev version tracks branch {self.target_branch} '
                f'of {self.repo_name}, checkouts.cfg not updated'
            )
            return

        checkouts = get_pickled_data(
            self.event.request.registry.settings['checkouts_file']
        )
        not_in_checkouts = [
            version
            for version in plone_versions
            if self.repo_name not in checkouts[version]
        ]
        if not not_in_checkouts:
            self.log(
                f'is already on checkouts.cfg of all plone '
                f'versions that it targets {plone_versions}'
            )
            return

        self.add_pacakge_to_checkouts(not_in_checkouts)

    def add_pacakge_to_checkouts(self, versions):
        """Add package to checkouts.cfg on buildout.coredev plone version"""
        last_commit = self.get_pull_request_last_commit()
        user = InputGitAuthor(
            last_commit.commit.author.name,
            last_commit.commit.author.email,
            datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        )
        org = self.github.get_organization('plone')
        repo = org.get_repo('buildout.coredev')

        for version in versions:
            attempts = 0
            while attempts < 5:
                try:
                    self.make_commit(repo, version, user)
                except GithubException:
                    attempts += 1
                    if attempts == 5:
                        self.log(
                            f'Could not update checkouts.cfg of {version} '
                            f'with {self.repo_name}',
                            level='warn',
                        )
                else:
                    self.log(f'add to checkouts.cfg of buildout.coredev {version}')
                    break

    def make_commit(self, repo, version, user):
        filename = u'checkouts.cfg'
        head_ref = repo.get_git_ref(f'heads/{version}')
        checkouts_cfg_file = repo.get_file_contents(filename, head_ref.object.sha)
        line = f'    {self.repo_name}\n'
        checkouts_content = checkouts_cfg_file.decoded_content.decode()
        checkouts_new_data = checkouts_content + line
        latest_commit = repo.get_git_commit(head_ref.object.sha)
        base_tree = latest_commit.tree
        mode = [t.mode for t in base_tree.tree if t.path == filename]
        if mode:
            mode = mode[0]
        else:
            mode = '100644'

        element = InputGitTreeElement(
            path=filename,
            mode=mode,
            type=checkouts_cfg_file.type,
            content=checkouts_new_data,
        )
        new_tree = repo.create_git_tree([element], base_tree)

        new_commit = repo.create_git_commit(
            f'[fc] Add {self.repo_name} to {filename}',
            new_tree,
            [latest_commit],
            user,
            user,
        )
        head_ref.edit(sha=new_commit.sha, force=False)


@subscriber(CommentOnPullRequest)
class TriggerPullRequestJenkinsJobs(object):
    def __init__(self, event):
        self.event = event

        self.run()

    @property
    def short_url(self):
        return shorten_comment_url(self.event.comment['html_url'])

    def log(self, msg, level='info'):
        if level == 'warn':
            logger.warning(f'COMMENT {self.short_url}: {msg}')
            return
        logger.info(f'COMMENT {self.short_url}: {msg}')

    def run(self):
        if self._should_trigger_jobs():
            plone_versions = self._which_plone_versions()
            self._trigger_jobs(plone_versions)

    def _should_trigger_jobs(self):
        pull_request_url = self.event.pull_request['html_url']
        repo_name = pull_request_url.split('/')[-3]
        if repo_name in IGNORE_NO_TEST_NEEDED:
            self.log('skip triggering jenkins jobs, repo is whitelisted')
            return False

        return '@jenkins-plone-org please run jobs' in self.event.comment['body']

    def _which_plone_versions(self):
        response = requests.get(self.event.pull_request['url'])
        if response.status_code != 200:
            self.log('Could not get information regarding pull request', level='warn')
            return []

        data = response.json()
        target_branch = data['base']['ref']
        repo_full_name = data['base']['repo']['full_name']

        plone_versions = plone_versions_targeted(
            repo_full_name, target_branch, self.event.request
        )

        tracked_versions = self.event.request.registry.settings['plone_versions']
        if (
            repo_full_name == 'plone/buildout.coredev'
            and target_branch in tracked_versions
        ):
            plone_versions = (target_branch,)

        elif not plone_versions:
            self.log('Does not target any Plone version')

        return plone_versions

    def _trigger_jobs(self, plone_versions):
        settings = self.event.request.registry.settings
        py3_versions = settings['py3_versions']

        for version in plone_versions:
            self._create_job(version)
            if version == '5.2':
                for python in py3_versions:
                    self._create_job(f'{version}-{python}')

    def _create_job(self, version):
        settings = self.event.request.registry.settings
        jenkins_user = settings['jenkins_user_id']
        jenkins_token = settings['jenkins_user_token']
        pull_request_url = self.event.pull_request['html_url']

        requests.post(
            f'https://jenkins.plone.org/job/pull-request-{version}/buildWithParameters',
            auth=(jenkins_user, jenkins_token),
            data={'PULL_REQUEST_URL': pull_request_url},
        )
        self.log(f'Triggered jenkins job for PR {version}.')


@subscriber(NewPullRequest)
class ExplainHowToTriggerJenkinsJobs(PullRequestSubscriber):
    def run(self):
        plone_versions = plone_versions_targeted(
            self.repo_full_name, self.target_branch, self.event.request
        )
        if not plone_versions:
            return

        user = self.pull_request['user']['login']
        msg = (
            f'@{user} thanks for creating this Pull Request and help improve Plone!\n\n'
            'To ensure that these changes do not break other parts of Plone, '
            'the Plone test suite matrix needs to pass.\n\n'
            'Whenever you feel that the pull request is ready to be tested, '
            'either start all jenkins jobs pull requests by yourself, '
            'or simply add a comment in this pull request stating:\n\n'
            '```\n'
            '@jenkins-plone-org please run jobs\n'
            '```\n\n'
            'With this simple comment all the jobs will be started automatically.\n\n'
            'Happy hacking!'
        )
        self.g_issue.create_comment(body=msg)
