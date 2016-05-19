# -*- coding: utf-8 -*-
from mr.roboto.subscriber import WarnTestsNeedToRun
from tempfile import NamedTemporaryFile
from testfixtures import LogCapture

import copy
import mock
import os
import pickle
import unittest


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
            'owner': {
                'login': 'plone',
            },
        },
    },
}

COREDEV_PAYLOAD = copy.deepcopy(PAYLOAD)
COREDEV_PAYLOAD['html_url'] = 'https://github.com/plone/buildout.coredev/pull/3'  # noqa
COREDEV_PAYLOAD['base']['ref'] = '4.3'
COREDEV_PAYLOAD['base']['repo']['name'] = 'buildout.coredev'
COREDEV_PAYLOAD['base']['repo']['full_name'] = 'plone/buildout.coredev'

COREDEV_RANDOM_BRANCH_PAYLOAD = copy.deepcopy(COREDEV_PAYLOAD)
COREDEV_RANDOM_BRANCH_PAYLOAD['base']['ref'] = 'random'


class MockRequest(object):

    def __init__(self):
        self._settings = {
            'github': mock.MagicMock(),
            'plone_versions': ['4.3', '5.1', ],
        }

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    def set_sources(self, data):
        with NamedTemporaryFile(delete=False) as tmp_file:
            sources_pickle = tmp_file.name
            with open(sources_pickle, 'w') as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(data))

        self._settings['sources_file'] = sources_pickle

    def cleanup_sources(self):
        if os.path.exists(self._settings['sources_file']):
            os.remove(self._settings['sources_file'])


class WarnPullRequestSubscriberTest(unittest.TestCase):

    def create_event(self, sources_data, payload=None):
        from mr.roboto.events import NewPullRequest
        if not payload:
            payload = PAYLOAD

        request = MockRequest()
        request.set_sources(sources_data)
        event = NewPullRequest(
            pull_request=payload,
            request=request,
        )
        return event

    def test_not_targeting_any_source(self):
        event = self.create_event(
            {
                ('plone/mr.roboto', 'stable'): ['5.1', ],
            },
        )

        with LogCapture() as captured_data:
            WarnTestsNeedToRun(event)

        event.request.cleanup_sources()

        self.assertEqual(
            len(captured_data.records),
            1
        )
        self.assertIn(
            'does not target any Plone version',
            captured_data.records[0].msg
        )

    def test_target_one_plone_version(self):
        event = self.create_event(
            {
                ('plone/mr.roboto', 'master'): ['5.1', ],
            },
        )

        with LogCapture() as captured_data:
            WarnTestsNeedToRun(event)

        event.request.cleanup_sources()

        self.assertEqual(
            len(captured_data.records),
            1
        )
        self.assertIn(
            'created pending status for plone 5.1',
            captured_data.records[0].msg
        )

    def test_target_multiple_plone_versions(self):
        event = self.create_event(
            {
                ('plone/mr.roboto', 'master'): ['5.1', '4.3', ],
            },
        )

        with LogCapture() as captured_data:
            WarnTestsNeedToRun(event)

        event.request.cleanup_sources()

        self.assertEqual(
            len(captured_data.records),
            2
        )

        messages = sorted([m.msg for m in captured_data.records])

        self.assertIn(
            'created pending status for plone 4.3',
            messages[0]
        )

        self.assertIn(
            'created pending status for plone 5.1',
            messages[1]
        )

    def test_buildout_coredev_not_targeting_plone_release(self):
        event = self.create_event(
            {},
            payload=COREDEV_RANDOM_BRANCH_PAYLOAD
        )

        with LogCapture() as captured_data:
            WarnTestsNeedToRun(event)

        event.request.cleanup_sources()

        self.assertEqual(
            len(captured_data.records),
            1
        )

        self.assertIn(
            'PR plone/buildout.coredev#3: does not target any Plone version',
            captured_data.records[0].msg
        )

    def test_buildout_coredev_targeting_plone_release(self):
        event = self.create_event({}, payload=COREDEV_PAYLOAD)

        with LogCapture() as captured_data:
            WarnTestsNeedToRun(event)

        event.request.cleanup_sources()

        self.assertEqual(
            len(captured_data.records),
            1
        )

        self.assertIn(
            'created pending status for plone 4.3',
            captured_data.records[0].msg
        )
