# -*- coding: utf-8 -*-
from hashlib import sha1
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
NEW_PULL_REQUEST_PAYLOAD = {
    'action': 'opened',
    'pull_request': {
        'html_url': 'https://github.com/plone/mr.roboto/pull/1',
    },
}

UPDATED_PULL_REQUEST_PAYLOAD = copy.deepcopy(NEW_PULL_REQUEST_PAYLOAD)
UPDATED_PULL_REQUEST_PAYLOAD['action'] = 'synchronize'

UNKNOWN_PULL_REQUEST_ACTION_PAYLOAD = copy.deepcopy(NEW_PULL_REQUEST_PAYLOAD)
UNKNOWN_PULL_REQUEST_ACTION_PAYLOAD['action'] = 'unknown'


def minimal_main(global_config, **settings):
    from github import Github
    from pyramid.config import Configurator
    config = Configurator(settings=settings)
    config.include('cornice')

    config.registry.settings['plone_versions'] = settings['plone_versions']
    config.registry.settings['roboto_url'] = settings['roboto_url']
    config.registry.settings['api_key'] = settings['api_key']
    config.registry.settings['github'] = Github(
        settings['github_user'],
        settings['github_password']
    )
    config.scan('mr.roboto.views.pull_requests')
    config.end()
    return config.make_wsgi_app()


class RunCoreJobTest(unittest.TestCase, ):

    def setUp(self):
        self.settings = {
            'plone_versions': ['4.3', ],
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

    def test_update_pull_request(self):
        result = self.call_view(UPDATED_PULL_REQUEST_PAYLOAD)

        self.assertIn(
            'Handlers already took care of this pull request',
            result.body,
        )

    def test_unknown_pull_request_action(self):
        result = self.call_view(UNKNOWN_PULL_REQUEST_ACTION_PAYLOAD)

        self.assertIn(
            'pull request {0} not handled'.format(
                UNKNOWN_PULL_REQUEST_ACTION_PAYLOAD['pull_request']['html_url']
            ),
            result.body,
        )
