# -*- coding: utf-8 -*-
from mr.roboto.events import NewPullRequest
from mr.roboto.subscriber import WarnNoChangelogEntry
from testfixtures import LogCapture

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
    'diff_url': 'https://github.com/plone/mr.roboto/pull/34.diff',
    'base': {'repo': {'name': 'Products.CMFPlone', 'owner': {'login': 'plone'}}},
}

WHITELISTED_REPO_PAYLOAD = copy.deepcopy(PAYLOAD)
WHITELISTED_REPO_PAYLOAD['base']['repo']['name'] = 'documentation'

DIFF_NO_CHANGELOG = """
diff --git a/src/mr.roboto/setup.py b/src/mr.roboto/setup.py
index 2a20bdc..57ce05f 100644
--- a/src/mr.roboto/setup.py
+++ b/src/mr.roboto/setup.py
@@ -16,6 +16,7 @@
     'pyramid_debugtoolbar',
     'pytest',
     'WebTest',
+    'testfixtures',
 ]
 setup(
"""

DIFF_WITH_CHANGELOG = """
diff --git a/src/mr.roboto/CHANGES.rst b/src/mr.roboto/CHANGES.rst
index 2a20bdc..57ce05f 100644
--- a/src/mr.roboto/CHANGES.rst
+++ b/src/mr.roboto/CHANGES.rst
@@ -16,6 +16,7 @@
     'pyramid_debugtoolbar',
     'pytest',
     'WebTest',
+    'testfixtures',
 ]
 setup(
"""

DIFF_WITH_NEWS_ENTRY = """
diff --git a/src/mr.roboto/CHANGES.rst b/src/mr.roboto/news/1.bugfix
index 2a20bdc..57ce05f 100644
--- a/src/mr.roboto/news/1.bugfix
+++ b/src/mr.roboto/news/1.bugfix
@@ -16,6 +16,7 @@
     'pyramid_debugtoolbar',
     'pytest',
     'WebTest',
+    'testfixtures',
 ]
 setup(
"""

DIFF_WITH_CHANGELOG_ON_HISTORY_txt = """diff --git a/src/mr.roboto/HISTORY.rst b/src/mr.roboto/HISTORY.rst
index 2a20bdc..57ce05f 100644
--- a/src/mr.roboto/HISTORY.rst
+++ b/src/mr.roboto/HISTORY.rst
@@ -16,6 +16,7 @@
     'pyramid_debugtoolbar',
     'pytest',
     'WebTest',
+    'testfixtures',
 ]
 setup(
"""


class MockRequest(object):
    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return {
            'github': mock.MagicMock(),
            'roboto_url': 'http://jenkins.plone.org/roboto',
        }


class MockDiff(object):
    def __init__(self, data):
        self.data = data.encode()

    @property
    def encoding(self):
        return 'utf-8'

    @property
    def content(self):
        return self.data


class ChangeLogEntrySubscriberTest(unittest.TestCase):
    def test_repo_whitelisted(self):
        event = NewPullRequest(
            pull_request=WHITELISTED_REPO_PAYLOAD, request=MockRequest()
        )

        with LogCapture() as captured_data:
            WarnNoChangelogEntry(event)

        self.assertIn(
            'whitelisted for changelog entries', captured_data.records[-1].msg
        )

    @mock.patch('requests.get')
    def test_no_change_log_file(self, m1):
        m1.return_value = MockDiff(DIFF_NO_CHANGELOG)

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            WarnNoChangelogEntry(event)

        self.assertIn('changelog entry: error', captured_data.records[-1].msg)

    @mock.patch('requests.get')
    def test_with_change_log_file(self, m1):
        m1.return_value = MockDiff(DIFF_WITH_CHANGELOG)

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            WarnNoChangelogEntry(event)

        self.assertIn('changelog entry: success', captured_data.records[-1].msg)

    @mock.patch('requests.get')
    def test_with_news_entry(self, m1):
        m1.return_value = MockDiff(DIFF_WITH_NEWS_ENTRY)

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            WarnNoChangelogEntry(event)

        self.assertIn('changelog entry: success', captured_data.records[-1].msg)

    @mock.patch('requests.get')
    def test_with_change_log_file_history(self, m1):
        m1.return_value = MockDiff(DIFF_WITH_CHANGELOG_ON_HISTORY_txt)

        event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())

        with LogCapture() as captured_data:
            WarnNoChangelogEntry(event)

        self.assertIn('changelog entry: success', captured_data.records[-1].msg)
