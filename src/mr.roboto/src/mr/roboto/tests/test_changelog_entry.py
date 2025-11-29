from mr.roboto.events import NewPullRequest
from mr.roboto.subscribers import WarnNoChangelogEntry
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
    "diff_url": "https://github.com/plone/mr.roboto/pull/34.diff",
    "base": {"repo": {"name": "Products.CMFPlone", "owner": {"login": "plone"}}},
    "user": {"login": "random"},
}

IGNORED_REPO_PAYLOAD = copy.deepcopy(PAYLOAD)
IGNORED_REPO_PAYLOAD["base"]["repo"]["name"] = "documentation"

IGNORED_USER_PAYLOAD = copy.deepcopy(PAYLOAD)
IGNORED_USER_PAYLOAD["user"]["login"] = "dependabot[bot]"


DIFF_NO_CHANGELOG = """
diff --git a/src/mr.roboto/setup.py b/src/mr.roboto/setup.py
index 2a20bdc..57ce05f 100644
--- a/src/mr.roboto/setup.py
+++ b/src/mr.roboto/setup.py
@@ -16,5 +16,6 @@
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
@@ -16,5 +16,6 @@
     'pyramid_debugtoolbar',
     'pytest',
     'WebTest',
+    'testfixtures',
 ]
 setup(
"""

DIFF_WITH_NEWS_ENTRY = """
diff --git a/src/mr.roboto/news/1.bugfix b/src/mr.roboto/news/1.bugfix
index 2a20bdc..57ce05f 100644
--- a/src/mr.roboto/news/1.bugfix
+++ b/src/mr.roboto/news/1.bugfix
@@ -1,5 +1,6 @@
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
@@ -1,5 +1,6 @@
     'pyramid_debugtoolbar',
     'pytest',
     'WebTest',
+    'testfixtures',
 ]
 setup(
"""


class MockRequest:
    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return {
            "github": mock.MagicMock(),
            "roboto_url": "http://jenkins.plone.org/roboto",
        }


class MockDiff:
    def __init__(self, data):
        self.data = data.encode()

    @property
    def encoding(self):
        return "utf-8"

    @property
    def content(self):
        return self.data


def test_repo_ignored(caplog):
    event = NewPullRequest(pull_request=IGNORED_REPO_PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    WarnNoChangelogEntry(event)
    assert "no need to have a changelog entry" in caplog.records[-1].msg


def test_user_ignored(caplog):
    event = NewPullRequest(pull_request=IGNORED_USER_PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    WarnNoChangelogEntry(event)
    assert "no need to have a changelog entry" in caplog.records[-1].msg


@patch("requests.get")
def test_no_change_log_file(m1, caplog):
    m1.return_value = MockDiff(DIFF_NO_CHANGELOG)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    WarnNoChangelogEntry(event)
    assert "changelog entry: error" in caplog.records[-1].msg


@patch("requests.get")
def test_with_change_log_file(m1, caplog):
    m1.return_value = MockDiff(DIFF_WITH_CHANGELOG)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    WarnNoChangelogEntry(event)
    assert "changelog entry: success" in caplog.records[-1].msg


@patch("requests.get")
def test_with_news_entry(m1, caplog):
    m1.return_value = MockDiff(DIFF_WITH_NEWS_ENTRY)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    WarnNoChangelogEntry(event)
    assert "changelog entry: success" in caplog.records[-1].msg


@patch("requests.get")
def test_with_change_log_file_history(m1, caplog):
    m1.return_value = MockDiff(DIFF_WITH_CHANGELOG_ON_HISTORY_txt)
    event = NewPullRequest(pull_request=PAYLOAD, request=MockRequest())
    caplog.set_level(logging.INFO)
    WarnNoChangelogEntry(event)
    assert "changelog entry: success" in caplog.records[-1].msg
