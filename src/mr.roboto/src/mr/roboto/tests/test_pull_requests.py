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
NEW_PR_PAYLOAD = {
    'action': 'opened',
    'pull_request': {
        'html_url': 'https://github.com/plone/mr.roboto/pull/1',
        'merged': False,
    },
}

UPDATED_PR_PAYLOAD = copy.deepcopy(NEW_PR_PAYLOAD)
UPDATED_PR_PAYLOAD['action'] = 'synchronize'

UNKNOWN_PR_ACTION_PAYLOAD = copy.deepcopy(NEW_PR_PAYLOAD)
UNKNOWN_PR_ACTION_PAYLOAD['action'] = 'unknown'

CLOSED_NOT_MERGED_PR_ACTION_PAYLOAD = copy.deepcopy(NEW_PR_PAYLOAD)
CLOSED_NOT_MERGED_PR_ACTION_PAYLOAD['action'] = 'closed'

CLOSED_AND_MERGED_PR_ACTION_PAYLOAD = copy.deepcopy(NEW_PR_PAYLOAD)
CLOSED_AND_MERGED_PR_ACTION_PAYLOAD['action'] = 'closed'
CLOSED_AND_MERGED_PR_ACTION_PAYLOAD['pull_request']['merged'] = True


@pytest.fixture
def roboto():
    settings = {}
    app = minimal_main(settings, 'mr.roboto.views.pull_requests')
    roboto = BaseApp(app)
    return roboto


def prepare_data(settings, payload):
    body = urllib.parse.urlencode({'payload': json.dumps(payload)})
    hmac_value = hmac.new(settings['api_key'].encode(), body.encode(), sha1)
    digest = hmac_value.hexdigest()
    return digest, body


def call_view(roboto, payload):
    settings = roboto.app.registry.settings
    digest, body = prepare_data(settings, payload)
    result = roboto.post(
        '/run/pull-request',
        headers={'X-Hub_Signature': f'sha1={digest}'},
        params=body,
    )
    return result


def test_no_validation(roboto):
    result = roboto.post('/run/pull-request')
    assert result.json['message'] == 'Token not active'


def test_ping_answer(roboto):
    result = call_view(roboto, {'ping': 'true'})
    assert 'No action' in result.json['message']


def test_pull_request_view(roboto):
    result = call_view(roboto, NEW_PR_PAYLOAD)
    assert 'Handlers already took care of this pull request' in result.json['message']


def test_update_pull_request(roboto):
    result = call_view(roboto, UPDATED_PR_PAYLOAD)
    assert 'Handlers already took care of this pull request' in result.json['message']


def test_unknown_pull_request_action(roboto, caplog):
    caplog.set_level(logging.INFO)
    call_view(roboto, UNKNOWN_PR_ACTION_PAYLOAD)

    assert len(caplog.records) == 2
    msg = 'PR plone/mr.roboto#1: action "unknown" (merged: False) not handled'
    assert msg in caplog.records[-1].msg


def test_closed_not_merged_pull_request_action(roboto, caplog):
    caplog.set_level(logging.INFO)
    call_view(roboto, CLOSED_NOT_MERGED_PR_ACTION_PAYLOAD)

    assert len(caplog.records) == 2
    msg = 'PR plone/mr.roboto#1: action "closed" (merged: False) not handled'
    assert msg in caplog.records[-1].msg


def test_closed_and_merged_pull_request_action(roboto):
    result = call_view(roboto, CLOSED_AND_MERGED_PR_ACTION_PAYLOAD)
    assert 'Handlers already took care of this pull request' in result.json['message']
