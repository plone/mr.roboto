# -*- coding: utf-8 -*-
from hashlib import sha1
from testfixtures import LogCapture
from webtest import TestApp

import copy
import hmac
import json
import unittest
import urllib


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
COMMENT_PAYLOAD = {
    'action': 'created',
    'comment': {
        'html_url': 'https://github.com/plone/plone.api/pull/42#commitcomment-290382',
        'user': {'login': 'my-name'},
    },
    'issue': {
        'pull_request': {
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

EDITED_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
EDITED_COMMENT_PAYLOAD['action'] = 'edit'


def minimal_main(global_config, **settings):
    from github import Github
    from pyramid.config import Configurator

    config = Configurator(settings=settings)
    config.include('cornice')

    config.registry.settings['plone_versions'] = settings['plone_versions']
    config.registry.settings['roboto_url'] = settings['roboto_url']
    config.registry.settings['api_key'] = settings['api_key']
    config.registry.settings['jenkins_user_id'] = 'jenkins-plone-org'
    config.registry.settings['github'] = Github(
        settings['github_user'], settings['github_password']
    )
    config.scan('mr.roboto.views.comments')
    config.end()
    return config.make_wsgi_app()


class Base(unittest.TestCase):
    def setUp(self):
        self.settings = {
            'plone_versions': ['5.2'],
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'xyz1234mnop',
            'sources_file': 'sources_pickle',
            'checkouts_file': 'checkouts_pickle',
            'github_user': 'x',
            'github_password': 'x',
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

    def test_comment_non_created_action(self):
        with LogCapture() as captured_data:
            self.call_view(EDITED_COMMENT_PAYLOAD)

        logger_record = captured_data.records[-1].msg
        self.assertIn('COMMENT ', logger_record)
        self.assertIn('with action edit on pull request ', logger_record)

    def test_regular_pull_request_comment(self):
        result = self.call_view(COMMENT_PAYLOAD)
        self.assertIn('Thanks! Handlers already took care of this comment', result)
