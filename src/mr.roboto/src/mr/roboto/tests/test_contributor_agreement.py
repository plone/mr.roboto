# -*- coding: utf-8 -*-
from mr.roboto.subscriber import have_signed_contributors_agreement
from testfixtures import LogCapture
from webtest import TestApp

import copy
import mock
import unittest


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
PAYLOAD = {
    'number': '34',
    'html_url': 'https://github.com/plone/mr.roboto/pull/34',
    'commits_url': 'https://github.com/plone/mr.roboto/pull/34/commits',
    'base': {
        'repo': {
            'name': 'mr.roboto',
            'owner': {
                'login': 'plone',
            },
        },
    },
}
COLLECTIVE_PAYLOAD = copy.deepcopy(PAYLOAD)
COLLECTIVE_PAYLOAD['base']['repo']['owner']['login'] = 'collective'


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
    return config.make_wsgi_app()


class ContributorsAgreementSubscriberTest(unittest.TestCase, ):

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

    @mock.patch('requests.get')
    def test_error_getting_commits(self, m1):
        from mr.roboto.events import NewPullRequest
        from requests.exceptions import ReadTimeout
        m1.side_effect = ReadTimeout()

        class Request(object):

            @property
            def registry(self):
                return self

            @property
            def settings(self):
                return {
                    'github': mock.MagicMock()
                }

        event = NewPullRequest(
            pull_request=PAYLOAD,
            request=Request(),
        )

        with LogCapture() as captured_data:
            have_signed_contributors_agreement(event)

        self.assertEqual(
            len(captured_data.records),
            1
        )
        self.assertIn(
            'Error while trying to get commits from pull request',
            captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_error_parsing_commits_data(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData(object):

            def json(self):
                raise ValueError()

        m1.return_value = FakeCommitsData()

        class Request(object):

            @property
            def registry(self):
                return self

            @property
            def settings(self):
                return {
                    'github': mock.MagicMock()
                }

        event = NewPullRequest(
            pull_request=PAYLOAD,
            request=Request(),
        )

        with LogCapture() as captured_data:
            have_signed_contributors_agreement(event)

        self.assertEqual(
            len(captured_data.records),
            1
        )
        self.assertIn(
            'Error while getting JSON data from pull request',
            captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_error_no_author_on_commit(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData(object):

            def json(self):
                return [
                    {
                        'committer': {
                            'login': 'user',
                        },
                    },
                ]

        m1.return_value = FakeCommitsData()

        class Request(object):

            @property
            def registry(self):
                return self

            @property
            def settings(self):
                return {
                    'github': mock.MagicMock()
                }

        event = NewPullRequest(
            pull_request=PAYLOAD,
            request=Request(),
        )

        with LogCapture() as captured_data:
            have_signed_contributors_agreement(event)

        self.assertIn(
            'does not have author user info',
            captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_no_foundation_member(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData(object):

            def json(self):
                return [
                    {
                        'committer': {
                            'login': 'user',
                        },
                        'author': {
                            'login': 'user',
                        },
                    },
                ]

        m1.return_value = FakeCommitsData()

        class Request(object):

            @property
            def registry(self):
                return self

            @property
            def settings(self):
                inner_mock = mock.MagicMock()
                inner_mock.has_in_members.return_value = False
                mock_obj = mock.MagicMock()
                mock_obj.get_organization.return_value = inner_mock
                return {
                    'github': mock_obj
                }

        event = NewPullRequest(
            pull_request=PAYLOAD,
            request=Request(),
        )

        with LogCapture() as captured_data:
            have_signed_contributors_agreement(event)

        self.assertEqual(
            len(captured_data.records),
            1
        )
        self.assertIn(
            'Contributors Agreement report: error',
            captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_no_plone_org_also_works(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData(object):

            def json(self):
                return [
                    {
                        'committer': {
                            'login': 'user',
                        },
                    },
                ]

        m1.return_value = FakeCommitsData()

        class Request(object):

            @property
            def registry(self):
                return self

            @property
            def settings(self):
                return {
                    'github': mock.MagicMock()
                }

        event = NewPullRequest(
            pull_request=COLLECTIVE_PAYLOAD,
            request=Request(),
        )

        with LogCapture() as captured_data:
            have_signed_contributors_agreement(event)

        self.assertIn(
            'Contributors Agreement report: success',
            captured_data.records[-1].msg
        )
