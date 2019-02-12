# -*- coding: utf-8 -*-
from hashlib import sha1
from mr.roboto.subscriber import TriggerPullRequestJenkinsJobs
from mr.roboto.events import CommentOnPullRequest
from tempfile import NamedTemporaryFile
from testfixtures import LogCapture
from webtest import TestApp

import copy
import hmac
import json
import mock
import os
import pickle
import unittest
import urllib


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
COMMENT_PAYLOAD = {
    'action': 'created',
    'comment': {
        'html_url': 'https://github.com/plone/plone.api/pull/42#issuecomment-290382',
        'user': {'login': 'my-name'},
        'body': 'Some random comment here',
    },
    'issue': {
        'pull_request': {
            'url': 'https://github.com/plone/mr.roboto/pull/1',
            'html_url': 'https://github.com/plone/mr.roboto/pull/1',
            'merged': False,
        }
    },
}

NO_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
del NO_COMMENT_PAYLOAD['comment']

NO_ISSUE_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
del NO_ISSUE_PAYLOAD['issue']

NO_PULL_REQUEST_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
del NO_PULL_REQUEST_PAYLOAD['issue']['pull_request']

JENKINS_USER_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
JENKINS_USER_PAYLOAD['comment']['user']['login'] = 'jenkins-plone-org'

MR_ROBOTO_USER_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
MR_ROBOTO_USER_PAYLOAD['comment']['user']['login'] = 'mister-roboto'

EDITED_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
EDITED_COMMENT_PAYLOAD['action'] = 'edit'

WHITELISTED_PKG_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
WHITELISTED_PKG_PAYLOAD['comment'][
    'html_url'
] = 'https://github.com/plone/plone.releaser/pull/42#issuecomment-290382'
WHITELISTED_PKG_PAYLOAD['issue']['pull_request'][
    'html_url'
] = 'https://github.com/plone/plone.releaser/pull/1'

CAN_NOT_GET_PR_INFO_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
CAN_NOT_GET_PR_INFO_PAYLOAD['issue']['pull_request']['url'] = 'https://unkown.pr'

COREDEV_PR_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
COREDEV_PR_COMMENT_PAYLOAD['issue']['pull_request']['url'] = 'https://buildout.coredev'

TRIGGER_PY3_JOBS_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
TRIGGER_PY3_JOBS_PAYLOAD['comment']['body'] = '@jenkins-plone-org please run jobs'

TRIGGER_NO_PY3_JOBS_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
TRIGGER_NO_PY3_JOBS_PAYLOAD['comment']['body'] = '@jenkins-plone-org please run jobs'
TRIGGER_NO_PY3_JOBS_PAYLOAD['issue']['pull_request'][
    'url'
] = 'https://github.com/plone/plone.api/pull/1'


def minimal_main(global_config, **settings):
    from github import Github
    from pyramid.config import Configurator

    config = Configurator(settings=settings)
    config.include('cornice')

    config.registry.settings['plone_versions'] = settings['plone_versions']
    config.registry.settings['py3_versions'] = settings['py3_versions']
    config.registry.settings['roboto_url'] = settings['roboto_url']
    config.registry.settings['api_key'] = settings['api_key']
    config.registry.settings['jenkins_user_id'] = settings['jenkins_user_id']
    config.registry.settings['github_users'] = (
        settings['jenkins_user_id'],
        'mister-roboto',
    )
    config.registry.settings['jenkins_user_token'] = settings['jenkins_user_token']
    config.registry.settings['github'] = Github(
        settings['github_user'], settings['github_password']
    )
    config.scan('mr.roboto.views.comments')
    config.end()
    return config.make_wsgi_app()


class MockRequest(object):
    def __init__(self, settings):
        self._settings = settings

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, data):
        self._settings = data

    def set_sources(self, data):
        with NamedTemporaryFile(delete=False) as tmp_file:
            sources_pickle = tmp_file.name
            with open(sources_pickle, 'bw') as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(data))

        self._settings['sources_file'] = sources_pickle

    def cleanup_sources(self):
        if os.path.exists(self._settings['sources_file']):
            os.remove(self._settings['sources_file'])


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[0] == 'https://buildout.coredev':
        return MockResponse(
            {'base': {'ref': '5.2', 'repo': {'full_name': 'plone/buildout.coredev'}}},
            200,
        )
    elif args[0] == 'https://github.com/plone/mr.roboto/pull/1':
        return MockResponse(
            {'base': {'ref': 'master', 'repo': {'full_name': 'plone/mr.roboto'}}}, 200
        )
    elif args[0] == 'https://github.com/plone/plone.api/pull/1':
        return MockResponse(
            {'base': {'ref': 'master', 'repo': {'full_name': 'plone/plone.api'}}}, 200
        )

    return MockResponse(None, 404)


class Base(unittest.TestCase):
    def setUp(self):
        self.settings = {
            'plone_versions': ['5.1', '5.2'],
            'py3_versions': ['3.6', '3.7'],
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'xyz1234mnop',
            'sources_file': 'sources_pickle',
            'checkouts_file': 'checkouts_pickle',
            'github_user': 'x',
            'github_password': 'x',
            'jenkins_user_id': 'jenkins-plone-org',
            'jenkins_user_token': 'some-random-token',
        }
        app = minimal_main({}, **self.settings)
        self.roboto = TestApp(app)

    def prepare_data(self, payload):
        body = urllib.parse.urlencode({'payload': json.dumps(payload)})
        hmac_value = hmac.new(self.settings['api_key'].encode(), body.encode(), sha1)
        digest = hmac_value.hexdigest()
        return digest, body

    def call_view(self, payload):
        digest, body = self.prepare_data(payload)
        result = self.roboto.post(
            '/run/comment', headers={'X-Hub_Signature': f'sha1={digest}'}, params=body
        )
        return result


class HandleCommentTests(Base):
    def test_no_validation(self):
        res = self.roboto.post('/run/comment')
        self.assertIn('Token not active', res.ubody)

    def test_ping_answer(self):
        result = self.call_view({'ping': 'true'})

        self.assertIn('No action', result.ubody)

    def test_no_comment(self):
        result = self.call_view(NO_COMMENT_PAYLOAD)
        self.assertIn('Comment is missing in payload. No action.', result.ubody)

    def test_no_issue(self):
        result = self.call_view(NO_ISSUE_PAYLOAD)
        self.assertIn(
            'The comment is not from a pull request. No action.', result.ubody
        )

    def test_no_pull_request(self):
        result = self.call_view(NO_PULL_REQUEST_PAYLOAD)
        self.assertIn(
            'The comment is not from a pull request. No action.', result.ubody
        )

    def test_jenkins_comment(self):
        with LogCapture() as captured_data:
            result = self.call_view(JENKINS_USER_PAYLOAD)

        self.assertIn('Comment on PR ', result.ubody)
        self.assertIn(
            f' ignored as is from jenkins-plone-org. No action.', result.ubody
        )

        logger_record = captured_data.records[-1].msg
        self.assertIn('COMMENT ', logger_record)
        self.assertIn('IGNORED as it is from jenkins-plone-org', logger_record)

    def test_mr_roboto_comment(self):
        with LogCapture() as captured_data:
            result = self.call_view(MR_ROBOTO_USER_PAYLOAD)

        self.assertIn('Comment on PR ', result.ubody)
        self.assertIn(f' ignored as is from mister-roboto. No action.', result.ubody)

        logger_record = captured_data.records[-1].msg
        self.assertIn('COMMENT ', logger_record)
        self.assertIn('IGNORED as it is from mister-roboto', logger_record)

    def test_comment_non_created_action(self):
        with LogCapture() as captured_data:
            self.call_view(EDITED_COMMENT_PAYLOAD)

        logger_record = captured_data.records[-1].msg
        self.assertIn('COMMENT ', logger_record)
        self.assertIn('with action edit on pull request ', logger_record)

    def test_regular_pull_request_comment(self):
        result = self.call_view(COMMENT_PAYLOAD)
        self.assertIn('Thanks! Handlers already took care of this comment', result)


class TriggerPullRequestJenkinsJobsTests(Base):
    def _subscriber(self, payload, data):
        request = MockRequest(self.settings)
        request.set_sources(data)
        event = CommentOnPullRequest(
            payload['comment'], payload['issue']['pull_request'], request
        )
        return TriggerPullRequestJenkinsJobs(event)

    def test_short_url(self):
        subscriber = self._subscriber(COMMENT_PAYLOAD, {})
        self.assertEqual(subscriber.short_url, 'plone/plone.api#42-290382')

    def test_package_whitelisted_no_jobs_triggered(self):
        with LogCapture() as captured_data:
            self._subscriber(WHITELISTED_PKG_PAYLOAD, {})
        logger_record = captured_data.records[-1].msg
        self.assertIn(
            'skip triggering jenkins jobs, repo is whitelisted', logger_record
        )

    def test_random_comment_no_jobs_triggered(self):
        subscriber = self._subscriber(COMMENT_PAYLOAD, {})
        with LogCapture() as captured_data:
            result = subscriber._should_trigger_jobs()

        self.assertEqual(len(captured_data.records), 0)
        self.assertFalse(result)

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_can_not_get_pr_info(self, mock_get):
        subscriber = self._subscriber(CAN_NOT_GET_PR_INFO_PAYLOAD, {})
        with LogCapture() as captured_data:
            subscriber._which_plone_versions()

        logger_record = captured_data.records[-1].msg
        self.assertIn('Could not get information regarding pull request', logger_record)

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_coredev_pull_request(self, mock_get):
        sources = {('plone/mr.roboto', 'stable'): ['5.2']}
        subscriber = self._subscriber(COREDEV_PR_COMMENT_PAYLOAD, sources)
        versions = subscriber._which_plone_versions()
        self.assertIn('5.2', versions)

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_no_plone_target_pull_request(self, mock_get):
        sources = {('plone/mr.roboto', 'stable'): ['5.0']}
        subscriber = self._subscriber(COMMENT_PAYLOAD, sources)
        with LogCapture() as captured_data:
            versions = subscriber._which_plone_versions()

        self.assertEqual(versions, [])
        logger_record = captured_data.records[-1].msg
        self.assertIn('Does not target any Plone version', logger_record)

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    @mock.patch('requests.post')
    def test_trigger_py3_jobs(self, mock_get, mock_post):
        sources = {('plone/mr.roboto', 'master'): ['5.2']}
        with LogCapture() as captured_data:
            self._subscriber(TRIGGER_PY3_JOBS_PAYLOAD, sources)

        self.assertIn(
            'Triggered jenkins job for PR 5.2-3.7.', captured_data.records[-1].msg
        )
        self.assertIn(
            'Triggered jenkins job for PR 5.2-3.6.', captured_data.records[-2].msg
        )
        self.assertIn(
            'Triggered jenkins job for PR 5.2.', captured_data.records[-3].msg
        )

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    @mock.patch('requests.post')
    def test_trigger_no_py3_jobs(self, mock_get, mock_post):
        sources = {('plone/plone.api', 'master'): ['5.1']}
        with LogCapture() as captured_data:
            self._subscriber(TRIGGER_NO_PY3_JOBS_PAYLOAD, sources)

        self.assertEqual(len(captured_data.records), 1)
        self.assertIn('Triggered jenkins job for PR 5.1.', captured_data.records[0].msg)
