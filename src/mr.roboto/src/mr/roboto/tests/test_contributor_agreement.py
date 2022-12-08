from mr.roboto.subscriber import ContributorsAgreementSigned
from testfixtures import LogCapture

import copy
from unittest import mock
import unittest


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
PAYLOAD = {
    'number': '34',
    'html_url': 'https://github.com/plone/mr.roboto/pull/34',
    'commits_url': 'https://github.com/plone/mr.roboto/pull/34/commits',
    'base': {'repo': {'name': 'Products.CMFPlone', 'owner': {'login': 'plone'}}},
}
COLLECTIVE_PAYLOAD = copy.deepcopy(PAYLOAD)
COLLECTIVE_PAYLOAD['base']['repo']['owner']['login'] = 'collective'
WHITELISTED_PAYLOAD = copy.deepcopy(PAYLOAD)
WHITELISTED_PAYLOAD['base']['repo']['name'] = 'icalendar'


class MockRequest:
    def __init__(self):
        self._settings = {'github': mock.MagicMock()}

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, data):
        self._settings = data


class ContributorsAgreementSubscriberTest(unittest.TestCase):
    @mock.patch('requests.get')
    def test_error_getting_commits(self, m1):
        from mr.roboto.events import NewPullRequest
        from requests.exceptions import ReadTimeout

        m1.side_effect = ReadTimeout()

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertEqual(len(captured_data.records), 1)
        self.assertIn(
            'error while trying to get its commits', captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_error_parsing_commits_data(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData:
            def json(self):
                raise ValueError()

        m1.return_value = FakeCommitsData()

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertEqual(len(captured_data.records), 1)
        self.assertIn(
            'error while getting its commits in JSON', captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_error_no_author_on_commit(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData:
            def json(self):
                return [
                    {
                        'committer': {'login': 'user'},
                        'author': None,
                        'commit': {'author': {'name': 'My name'}},
                    }
                ]

        m1.return_value = FakeCommitsData()

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertIn('does not have author user info', captured_data.records[0].msg)

    @mock.patch('requests.get')
    def test_error_no_author_on_commit_no_duplicates(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData:
            def json(self):
                return [
                    {
                        'committer': {'login': 'user'},
                        'author': None,
                        'commit': {'author': {'name': 'My näme'}},
                    },
                    {
                        'committer': {'login': 'user'},
                        'author': None,
                        'commit': {'author': {'name': 'My name'}},
                    },
                    {
                        'committer': {'login': 'user'},
                        'author': None,
                        'commit': {'author': {'name': 'My name'}},
                    },
                ]

        m1.return_value = FakeCommitsData()

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertIn(
            'me missing contributors agreement', captured_data.records[-2].msg
        )

    @mock.patch('requests.get')
    def test_no_foundation_member(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData:
            def json(self):
                return [{'committer': {'login': 'user'}, 'author': {'login': 'user'}}]

        m1.return_value = FakeCommitsData()

        inner_mock = mock.MagicMock()
        inner_mock.has_in_members.return_value = False
        mock_obj = mock.MagicMock()
        mock_obj.get_organization.return_value = inner_mock
        settings = {'github': mock_obj}

        request = MockRequest()
        request.settings = settings

        event = NewPullRequest(pull_request=PAYLOAD, request=request)

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertEqual(len(captured_data.records), 1)
        self.assertIn(
            'Contributors Agreement report: error', captured_data.records[0].msg
        )

    @mock.patch('requests.get')
    def test_no_plone_org_also_works(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData:
            def json(self):
                return [
                    {
                        'committer': {'login': 'user'},
                        'author': {'login': 'user'},
                        'commit': {'author': {'name': 'My name'}},
                    }
                ]

        m1.return_value = FakeCommitsData()

        event = NewPullRequest(pull_request=COLLECTIVE_PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertIn(
            'Contributors Agreement report: success', captured_data.records[-1].msg
        )

    @mock.patch('requests.get')
    def test_ignore_witelisted_users(self, m1):
        from mr.roboto.events import NewPullRequest

        class FakeCommitsData:
            def json(self):
                return [
                    {'committer': {'login': 'web-flow'}, 'author': {'login': 'user'}}
                ]

        m1.return_value = FakeCommitsData()

        event = NewPullRequest(pull_request=COLLECTIVE_PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertIn(
            'Contributors Agreement report: success', captured_data.records[-1].msg
        )

    def test_whitelisted(self):
        from mr.roboto.events import NewPullRequest

        event = NewPullRequest(pull_request=WHITELISTED_PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            ContributorsAgreementSigned(event)

        self.assertIn(
            'whitelisted for contributors agreement', captured_data.records[-1].msg
        )
