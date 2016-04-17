# -*- coding: utf-8 -*-
from hashlib import sha1
from mr.roboto import main
from webtest import TestApp

import hmac
import json
import unittest
import urllib


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
NEW_PULL_REQUEST_PAYLOAD = {
    'action': 'opened',
    'pull_request': {
        'html_url': 'https://github.com/plone/mr.roboto/pull/1',
    },
}


class RunCoreJobTest(unittest.TestCase):

    def setUp(self):
        self.settings = {
            'plone_versions': '["4.3",]',
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'xyz1234mnop',
            'sources_file': 'sources_pickle',
            'checkouts_file': 'checkouts_pickle',
            'github_user': 'x',
            'github_password': 'x',
        }
        app = main({}, **self.settings)
        self.roboto = TestApp(app)

    def prepare_data(self, payload):
        body = urllib.urlencode(
            {'payload': json.dumps(payload)},
        )
        hmac_value = hmac.new(
            self.settings['api_key'],
            body,
            sha1,
        )
        digest = hmac_value.hexdigest()
        return digest, body

    def call_view(self, payload):
        digest, body = self.prepare_data(payload)
        result = self.roboto.post(
            '/run/pull-request',
            headers={
                'X-Hub_Signature': 'sha1={0}'.format(digest),
            },
            params=body,
        )
        return result

    def test_no_validation(self):
        res = self.roboto.post('/run/pull-request')
        self.assertIn(
            'Token not active',
            res.body,
        )

    def test_ping_answer(self):
        result = self.call_view({'ping': 'true'})

        self.assertIn(
            'No action',
            result.body,
        )

    def test_pull_request_view(self):
        result = self.call_view(NEW_PULL_REQUEST_PAYLOAD)

        self.assertIn(
            'Handlers already took care of this pull request',
            result.body,
        )
