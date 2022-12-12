from mr.roboto.subscriber import WarnTestsNeedToRun
from mr.roboto.tests import default_settings
from tempfile import NamedTemporaryFile
from unittest import mock

import copy
import logging
import os
import pickle


"""
Reduced set of data sent by Github about a pull request.

Each payload is adapted later on to test all corner cases.
"""
PAYLOAD = {
    'number': '45',
    'html_url': 'https://github.com/plone/mr.roboto/pull/34',
    'base': {
        'ref': 'master',
        'repo': {
            'full_name': 'plone/mr.roboto',
            'name': 'mr.roboto',
            'owner': {'login': 'plone'},
        },
    },
}

COREDEV_PAYLOAD = copy.deepcopy(PAYLOAD)
COREDEV_PAYLOAD['html_url'] = 'https://github.com/plone/buildout.coredev/pull/3'  # noqa
COREDEV_PAYLOAD['base']['ref'] = '6.0'
COREDEV_PAYLOAD['base']['repo']['name'] = 'buildout.coredev'
COREDEV_PAYLOAD['base']['repo']['full_name'] = 'plone/buildout.coredev'

COREDEV_RANDOM_BRANCH_PAYLOAD = copy.deepcopy(COREDEV_PAYLOAD)
COREDEV_RANDOM_BRANCH_PAYLOAD['base']['ref'] = 'random'

WHITELISTED_REPO = copy.deepcopy(PAYLOAD)
WHITELISTED_REPO['html_url'] = 'https://github.com/plone/plone.releaser/pull/5'
WHITELISTED_REPO['base']['repo']['full_name'] = 'plone/plone.releaser'
WHITELISTED_REPO['base']['repo']['name'] = 'plone.releaser'


class MockRequest:
    def __init__(self):
        self._settings = default_settings(github=mock.MagicMock())

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    def set_sources(self, data):
        with NamedTemporaryFile(delete=False) as tmp_file:
            sources_pickle = tmp_file.name
            with open(sources_pickle, 'bw') as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(data))

        self._settings['sources_file'] = sources_pickle

    def cleanup_sources(self):
        if os.path.exists(self._settings['sources_file']):
            os.remove(self._settings['sources_file'])


def create_event(sources_data, payload=None):
    from mr.roboto.events import NewPullRequest

    if not payload:
        payload = PAYLOAD

    request = MockRequest()
    request.set_sources(sources_data)
    event = NewPullRequest(pull_request=payload, request=request)
    return event


def test_not_targeting_any_source(caplog):
    caplog.set_level(logging.INFO)
    event = create_event({('plone/mr.roboto', 'stable'): ['5.1']})
    WarnTestsNeedToRun(event)
    event.request.cleanup_sources()

    assert len(caplog.records) == 1
    assert 'does not target any Plone version', caplog.records[-1].msg


def test_target_one_plone_version(caplog):
    caplog.set_level(logging.INFO)
    event = create_event({('plone/mr.roboto', 'master'): ['5.2']})
    WarnTestsNeedToRun(event)
    event.request.cleanup_sources()

    assert len(caplog.records) == 2
    assert 'created pending status for plone 5.2 on python 2.7' in caplog.records[0].msg
    assert 'created pending status for plone 5.2 on python 3.6' in caplog.records[1].msg


def test_target_multiple_plone_versions(caplog):
    caplog.set_level(logging.INFO)
    event = create_event({('plone/mr.roboto', 'master'): ['5.2', '6.0']})
    WarnTestsNeedToRun(event)
    event.request.cleanup_sources()

    assert len(caplog.records) == 4
    messages = sorted([m.msg for m in caplog.records])
    pairs = (('5.2', '2.7'), ('5.2', '3.6'), ('6.0', '3.8'), ('6.0', '3.9'))
    for pair, msg in zip(pairs, messages):
        plone, python = pair
        assert f'created pending status for plone {plone} on python {python}' in msg


def test_buildout_coredev_not_targeting_plone_release(caplog):
    caplog.set_level(logging.INFO)
    event = create_event({}, payload=COREDEV_RANDOM_BRANCH_PAYLOAD)
    WarnTestsNeedToRun(event)
    event.request.cleanup_sources()

    assert len(caplog.records) == 1
    assert (
        'PR plone/buildout.coredev#3: does not target any Plone version'
        in caplog.records[0].msg
    )


def test_buildout_coredev_targeting_plone_release(caplog):
    caplog.set_level(logging.INFO)
    event = create_event({}, payload=COREDEV_PAYLOAD)
    WarnTestsNeedToRun(event)
    event.request.cleanup_sources()

    assert len(caplog.records) == 2
    assert 'for plone 6.0 on python 3.8' in caplog.records[0].msg
    assert 'for plone 6.0 on python 3.9' in caplog.records[1].msg


def test_whitelisted(caplog):
    caplog.set_level(logging.INFO)
    event = create_event({}, payload=WHITELISTED_REPO)
    WarnTestsNeedToRun(event)
    event.request.cleanup_sources()

    assert len(caplog.records) == 1
    assert 'skip adding test warnings, repo whitelisted' in caplog.records[0].msg
