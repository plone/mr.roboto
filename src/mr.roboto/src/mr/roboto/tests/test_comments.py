from hashlib import sha1
from mr.roboto.tests import minimal_main
from webtest import TestApp as BaseApp

import copy
import hmac
import json
import logging
import pytest
import urllib


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
COMMENT_PAYLOAD = {
    "action": "created",
    "comment": {
        "html_url": "https://github.com/plone/plone.api/pull/42#issuecomment-290382",
        "user": {"login": "my-name"},
        "body": "Some random comment here",
    },
    "issue": {
        "pull_request": {
            "url": "https://github.com/plone/mr.roboto/pull/1",
            "html_url": "https://github.com/plone/mr.roboto/pull/1",
            "merged": False,
        }
    },
}

NO_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
del NO_COMMENT_PAYLOAD["comment"]

NO_ISSUE_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
del NO_ISSUE_PAYLOAD["issue"]

NO_PULL_REQUEST_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
del NO_PULL_REQUEST_PAYLOAD["issue"]["pull_request"]

JENKINS_USER_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
JENKINS_USER_PAYLOAD["comment"]["user"]["login"] = "jenkins-plone-org"

MR_ROBOTO_USER_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
MR_ROBOTO_USER_PAYLOAD["comment"]["user"]["login"] = "mister-roboto"

EDITED_COMMENT_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
EDITED_COMMENT_PAYLOAD["action"] = "edit"

TRIGGER_NO_PY3_JOBS_PAYLOAD = copy.deepcopy(COMMENT_PAYLOAD)
TRIGGER_NO_PY3_JOBS_PAYLOAD["comment"]["body"] = "@jenkins-plone-org please run jobs"
TRIGGER_NO_PY3_JOBS_PAYLOAD["issue"]["pull_request"][
    "url"
] = "https://github.com/plone/plone.api/pull/1"


@pytest.fixture
def roboto():
    settings = {}
    app = minimal_main(settings, "mr.roboto.views.comments")
    roboto = BaseApp(app)
    return roboto


def prepare_data(settings, payload):
    body = urllib.parse.urlencode({"payload": json.dumps(payload)})
    hmac_value = hmac.new(settings["api_key"].encode(), body.encode(), sha1)
    digest = hmac_value.hexdigest()
    return digest, body


def call_view(roboto, payload):
    settings = roboto.app.registry.settings
    digest, body = prepare_data(settings, payload)
    result = roboto.post(
        "/run/comment", headers={"X-Hub_Signature": f"sha1={digest}"}, params=body
    )
    return result


def test_no_validation(roboto):
    result = roboto.post("/run/comment")
    assert result.json["message"] == "Token not active"


def test_ping_answer(roboto):
    result = call_view(roboto, {"ping": "true"})
    assert result.json["message"] == "No action"


def test_no_comment(roboto):
    result = call_view(roboto, NO_COMMENT_PAYLOAD)
    assert result.json["message"] == "Comment is missing in payload. No action."


def test_no_issue(roboto):
    result = call_view(roboto, NO_ISSUE_PAYLOAD)
    assert (
        result.json["message"] == "The comment is not from a pull request. No action."
    )


def test_no_pull_request(roboto):
    result = call_view(roboto, NO_PULL_REQUEST_PAYLOAD)
    assert (
        result.json["message"] == "The comment is not from a pull request. No action."
    )


def test_jenkins_comment(roboto, caplog):
    caplog.set_level(logging.INFO)
    result = call_view(roboto, JENKINS_USER_PAYLOAD)
    assert "Comment on PR " in result.ubody
    assert " ignored as is from jenkins-plone-org. No action." in result.ubody

    logger_record = caplog.records[-1].msg
    assert "COMMENT " in logger_record
    assert "IGNORED as it is from jenkins-plone-org" in logger_record


def test_mr_roboto_comment(roboto, caplog):
    caplog.set_level(logging.INFO)
    result = call_view(roboto, MR_ROBOTO_USER_PAYLOAD)

    assert "Comment on PR " in result.ubody
    assert " ignored as is from mister-roboto. No action." in result.ubody

    logger_record = caplog.records[-1].msg
    assert "COMMENT " in logger_record
    assert "IGNORED as it is from mister-roboto" in logger_record


def test_comment_non_created_action(roboto, caplog):
    caplog.set_level(logging.INFO)
    call_view(roboto, EDITED_COMMENT_PAYLOAD)

    logger_record = caplog.records[-1].msg
    assert "COMMENT " in logger_record
    assert "with action edit on pull request " in logger_record


def test_regular_pull_request_comment(roboto):
    result = call_view(roboto, COMMENT_PAYLOAD)
    assert (
        "Thanks! Handlers already took care of this comment" in result.json["message"]
    )
