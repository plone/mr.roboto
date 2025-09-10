from mr.roboto.events import NewPullRequest
from mr.roboto.subscribers import ContributorsAgreementSigned
from unittest import mock
from unittest.mock import patch

import copy
import logging


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
PAYLOAD = {
    "number": "34",
    "html_url": "https://github.com/plone/mr.roboto/pull/34",
    "commits_url": "https://github.com/plone/mr.roboto/pull/34/commits",
    "base": {"repo": {"name": "Products.CMFPlone", "owner": {"login": "plone"}}},
}
COLLECTIVE_PAYLOAD = copy.deepcopy(PAYLOAD)
COLLECTIVE_PAYLOAD["base"]["repo"]["owner"]["login"] = "collective"
IGNORED_PAYLOAD = copy.deepcopy(PAYLOAD)
IGNORED_PAYLOAD["base"]["repo"]["name"] = "icalendar"


class MockRequest:
    def __init__(self):
        self._settings = {"github": mock.MagicMock()}

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, data):
        self._settings = data


@patch("requests.get")
def test_error_getting_commits(m1, caplog):
    from requests.exceptions import ReadTimeout

    m1.side_effect = ReadTimeout()
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    ContributorsAgreementSigned(event)

    assert len(caplog.records) == 1
    assert "error while trying to get its commits" in caplog.records[0].msg


@patch("requests.get")
def test_error_parsing_commits_data(m1, caplog):
    class FakeCommitsData:
        def json(self):
            raise ValueError()

    m1.return_value = FakeCommitsData()
    caplog.set_level(logging.INFO)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    ContributorsAgreementSigned(event)

    assert len(caplog.records) == 1
    assert "error while getting its commits in JSON" in caplog.records[0].msg


@patch("requests.get")
def test_error_no_author_on_commit(m1, caplog):
    class FakeCommitsData:
        def json(self):
            return [
                {
                    "committer": {"login": "user"},
                    "author": None,
                    "commit": {"author": {"name": "My name"}},
                }
            ]

    m1.return_value = FakeCommitsData()
    caplog.set_level(logging.INFO)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    ContributorsAgreementSigned(event)

    assert "does not have author user info" in caplog.records[0].msg


@patch("requests.get")
def test_error_no_author_on_commit_no_duplicates(m1, caplog):
    class FakeCommitsData:
        def json(self):
            return [
                {
                    "committer": {"login": "user"},
                    "author": None,
                    "commit": {"author": {"name": "My näme"}},
                },
                {
                    "committer": {"login": "user"},
                    "author": None,
                    "commit": {"author": {"name": "My name"}},
                },
                {
                    "committer": {"login": "user"},
                    "author": None,
                    "commit": {"author": {"name": "My name"}},
                },
            ]

    m1.return_value = FakeCommitsData()
    caplog.set_level(logging.INFO)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    ContributorsAgreementSigned(event)

    assert "me missing contributors agreement" in caplog.records[-2].msg


@patch("requests.get")
def test_no_foundation_member(m1, caplog):
    class FakeCommitsData:
        def json(self):
            return [{"committer": {"login": "user"}, "author": {"login": "user"}}]

    m1.return_value = FakeCommitsData()
    caplog.set_level(logging.INFO)
    inner_mock = mock.MagicMock()
    inner_mock.has_in_members.return_value = False
    mock_obj = mock.MagicMock()
    mock_obj.get_organization.return_value = inner_mock
    settings = {"github": mock_obj}

    request = MockRequest()
    request.settings = settings
    event = NewPullRequest(pull_request=PAYLOAD, request=request)
    ContributorsAgreementSigned(event)

    assert len(caplog.records) == 1
    assert "Contributors Agreement report: error" in caplog.records[0].msg


@patch("requests.get")
def test_no_plone_org_also_works(m1, caplog):
    class FakeCommitsData:
        def json(self):
            return [
                {
                    "committer": {"login": "user"},
                    "author": {"login": "user"},
                    "commit": {"author": {"name": "My name"}},
                }
            ]

    m1.return_value = FakeCommitsData()
    event = NewPullRequest(pull_request=COLLECTIVE_PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    ContributorsAgreementSigned(event)

    assert "Contributors Agreement report: success" in caplog.records[-1].msg


@patch("requests.get")
def test_ignore_witelisted_users(m1, caplog):
    class FakeCommitsData:
        def json(self):
            return [{"committer": {"login": "web-flow"}, "author": {"login": "user"}}]

    m1.return_value = FakeCommitsData()
    event = NewPullRequest(pull_request=COLLECTIVE_PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    ContributorsAgreementSigned(event)

    assert "Contributors Agreement report: success" in caplog.records[-1].msg


def test_ignored(caplog):
    event = NewPullRequest(pull_request=IGNORED_PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    ContributorsAgreementSigned(event)

    assert "no need to sign contributors agreement" in caplog.records[-1].msg
