from mr.roboto.events import CommentOnPullRequest
from mr.roboto.subscribers import TriggerPullRequestJenkinsJobs
from mr.roboto.tests import minimal_main
from mr.roboto.tests.test_comments import COMMENT_PAYLOAD
from tempfile import NamedTemporaryFile
from unittest.mock import patch
from webtest import TestApp as BaseApp

import copy
import logging
import pickle
import pytest


IGNORED_PKG_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
IGNORED_PKG_PAYLOAD["comment"][
    "html_url"
] = "https://github.com/plone/plone.releaser/pull/42#issuecomment-290382"
IGNORED_PKG_PAYLOAD["issue"]["pull_request"][
    "html_url"
] = "https://github.com/plone/plone.releaser/pull/1"

CAN_NOT_GET_PR_INFO_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
CAN_NOT_GET_PR_INFO_PAYLOAD["issue"]["pull_request"]["url"] = "https://unknown.pr"

COREDEV_PR_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
COREDEV_PR_COMMENT_PAYLOAD["issue"]["pull_request"]["url"] = "https://buildout.coredev"

TRIGGER_PY3_JOBS_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
TRIGGER_PY3_JOBS_PAYLOAD["comment"]["body"] = "@jenkins-plone-org please run jobs"


class MockRequest:
    def __init__(self, settings):
        self._settings = settings

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    def set_sources(self, data):
        with NamedTemporaryFile(delete=False) as tmp_file:
            sources_pickle = tmp_file.name
            with open(sources_pickle, "bw") as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(data))

        self._settings["sources_file"] = sources_pickle


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[0] == "https://buildout.coredev":
        return MockResponse(
            {"base": {"ref": "5.2", "repo": {"full_name": "plone/buildout.coredev"}}},
            200,
        )
    elif args[0] == "https://github.com/plone/mr.roboto/pull/1":
        return MockResponse(
            {"base": {"ref": "master", "repo": {"full_name": "plone/mr.roboto"}}}, 200
        )

    return MockResponse(None, 404)


@pytest.fixture
def roboto():
    settings = {}
    app = minimal_main(settings, "mr.roboto.views.comments")
    roboto = BaseApp(app)
    return roboto


def _subscriber(roboto, payload, data):
    settings = roboto.app.registry.settings
    request = MockRequest(settings)
    request.set_sources(data)
    event = CommentOnPullRequest(
        payload["comment"], payload["issue"]["pull_request"], request
    )
    return TriggerPullRequestJenkinsJobs(event)


def test_short_url(roboto):
    subscriber = _subscriber(roboto, COMMENT_PAYLOAD, {})
    assert subscriber.short_url == "plone/plone.api#42-290382"


def test_package_ignoed_no_jobs_triggered(roboto, caplog):
    caplog.set_level(logging.INFO)
    _subscriber(roboto, IGNORED_PKG_PAYLOAD, {})
    logger_record = caplog.records[-1].msg
    assert "skip triggering jenkins jobs, repo is ignored" in logger_record


def test_random_comment_no_jobs_triggered(roboto, caplog):
    caplog.set_level(logging.INFO)
    subscriber = _subscriber(roboto, COMMENT_PAYLOAD, {})
    result = subscriber._should_trigger_jobs()

    assert len(caplog.records) == 0
    assert result is False


@patch("requests.get", side_effect=mocked_requests_get)
def test_can_not_get_pr_info(mock_get, roboto, caplog):
    caplog.set_level(logging.INFO)
    subscriber = _subscriber(roboto, CAN_NOT_GET_PR_INFO_PAYLOAD, {})
    subscriber._which_plone_versions()

    logger_record = caplog.records[-1].msg
    assert "Could not get information regarding pull request" in logger_record


@patch("requests.get", side_effect=mocked_requests_get)
def test_coredev_pull_request(mock_get, roboto):
    sources = {("plone/mr.roboto", "stable"): ["5.2"]}
    subscriber = _subscriber(roboto, COREDEV_PR_COMMENT_PAYLOAD, sources)
    versions = subscriber._which_plone_versions()
    assert "5.2" in versions


@patch("requests.get", side_effect=mocked_requests_get)
def test_no_plone_target_pull_request(mock_get, roboto, caplog):
    caplog.set_level(logging.INFO)
    sources = {("plone/mr.roboto", "stable"): ["5.0"]}
    subscriber = _subscriber(roboto, COMMENT_PAYLOAD, sources)
    versions = subscriber._which_plone_versions()

    assert versions == []
    logger_record = caplog.records[-1].msg
    assert "Does not target any Plone version" in logger_record


@patch("requests.get", side_effect=mocked_requests_get)
@patch("requests.post")
def test_trigger_py3_jobs(mock_get, mock_post, roboto, caplog):
    caplog.set_level(logging.INFO)
    sources = {("plone/mr.roboto", "master"): ["5.2"]}
    _subscriber(roboto, TRIGGER_PY3_JOBS_PAYLOAD, sources)

    assert "Triggered jenkins job for PR 5.2-3.6." in caplog.records[-1].msg
    assert "Triggered jenkins job for PR 5.2-2.7." in caplog.records[-2].msg
