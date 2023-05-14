from mr.roboto.events import MergedPullRequest
from mr.roboto.subscriber import UpdateCoredevCheckouts
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
    "number": "45",
    "html_url": "https://github.com/plone/buildout.coredev/pull/34567",
    "base": {
        "repo": {
            "full_name": "plone/buildout.coredev",
            "name": "buildout.coredev",
            "owner": {"login": "plone"},
        }
    },
    "user": {"login": "mr.bean"},
}

NO_PLONE_VERSION_PAYLOAD = copy.deepcopy(PAYLOAD)
NO_PLONE_VERSION_PAYLOAD[
    "html_url"
] = "https://github.com/plone/plone.uuid/pull/3"  # noqa
NO_PLONE_VERSION_PAYLOAD["base"]["ref"] = "my-upstream-branch"
NO_PLONE_VERSION_PAYLOAD["base"]["repo"]["name"] = "plone.uuid"
NO_PLONE_VERSION_PAYLOAD["base"]["repo"]["full_name"] = "plone/plone.uuid"


PLONE_VERSION_PAYLOAD = copy.deepcopy(NO_PLONE_VERSION_PAYLOAD)
PLONE_VERSION_PAYLOAD["base"]["ref"] = "master"


class FakeGithub:
    def get_organization(self, name):
        return self

    def get_repo(self, name):
        return self

    def get_git_ref(self, name):
        class HEAD:
            @property
            def object(self):
                return self

            @property
            def sha(self):
                return "shaaaaa"

            def edit(self, sha=None, force=False):
                return

        return HEAD()

    def get_contents(self, name, sha):
        return self

    @property
    def decoded_content(self):
        return b"some text"

    def get_git_commit(self, sha):
        return self

    @property
    def tree(self):
        return mock.MagicMock()

    @property
    def type(self):
        return "file"

    def create_git_commit(self, one, two, three, four, five):
        return mock.MagicMock()

    def create_git_tree(self, one, two):
        return mock.MagicMock()

    def get_pull(self, one):
        return self

    def get_commits(self):
        return self

    @property
    def reversed(self):
        return [self]

    @property
    def commit(self):
        return self

    @property
    def author(self):
        return self

    @property
    def name(self):
        return "someone"

    @property
    def email(self):
        return "hi@dummy.com"


class MockRequest:
    def __init__(self):
        self._settings = {"github": FakeGithub(), "plone_versions": ["4.3", "5.1"]}

    @property
    def registry(self):
        return self

    @property
    def settings(self):
        return self._settings

    def set_data(self, data, key):
        with NamedTemporaryFile(delete=False) as tmp_file:
            pickle_filename = tmp_file.name
            with open(pickle_filename, "bw") as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(data))

        self._settings[key] = pickle_filename

    def set_checkouts(self, data):
        self.set_data(data, "checkouts_file")

    def set_sources(self, data):
        self.set_data(data, "sources_file")

    def cleanup(self):
        if os.path.exists(self._settings["checkouts_file"]):
            os.remove(self._settings["checkouts_file"])
        if os.path.exists(self._settings["sources_file"]):
            os.remove(self._settings["sources_file"])


def create_event(checkouts_data, sources_data, payload):
    request = MockRequest()
    request.set_checkouts(checkouts_data)
    request.set_sources(sources_data)
    event = MergedPullRequest(pull_request=payload, request=request)
    return event


def test_buildout_coredev_merge(caplog):
    event = create_event({}, {}, payload=PAYLOAD)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()
    assert len(caplog.records) == 0


def test_not_targeting_any_plone_version(caplog):
    event = create_event({}, {}, payload=NO_PLONE_VERSION_PAYLOAD)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()

    assert len(caplog.records) == 1
    assert (
        "no plone coredev version tracks branch my-upstream-branch of "
        "plone.uuid, checkouts.cfg not updated"
    ) in caplog.records[0].msg


def test_in_checkouts(caplog):
    checkouts = {"5.1": ["plone.uuid"]}
    sources = {("plone/plone.uuid", "master"): ["5.1"]}
    event = create_event(checkouts, sources, payload=PLONE_VERSION_PAYLOAD)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()

    assert len(caplog.records) == 1
    assert (
        "is already on checkouts.cfg of all plone versions that it targets"
    ) in caplog.records[0].msg


def test_in_multiple_checkouts(caplog):
    checkouts = {"5.0": ["plone.uuid"], "5.1": ["plone.uuid"]}
    sources = {("plone/plone.uuid", "master"): ["5.1", "5.0"]}
    event = create_event(checkouts, sources, payload=PLONE_VERSION_PAYLOAD)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()

    assert len(caplog.records) == 1
    assert (
        "is already on checkouts.cfg of all plone versions that it targets"
    ) in caplog.records[0].msg


def test_not_in_checkouts(caplog):
    checkouts = {"5.0": [], "5.1": ["plone.uuid"]}
    sources = {("plone/plone.uuid", "master"): ["5.1", "5.0"]}
    event = create_event(checkouts, sources, payload=PLONE_VERSION_PAYLOAD)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()

    assert len(caplog.records) == 1
    assert "add to checkouts.cfg of buildout.coredev 5.0" in caplog.records[0].msg


def test_not_in_multiple_checkouts(caplog):
    checkouts = {"4.3": [], "5.0": [], "5.1": ["plone.uuid"]}
    sources = {("plone/plone.uuid", "master"): ["5.1", "5.0", "4.3"]}
    event = create_event(checkouts, sources, payload=PLONE_VERSION_PAYLOAD)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()

    assert len(caplog.records) == 2
    assert "add to checkouts.cfg of buildout.coredev 5.0" in caplog.records[0].msg
    assert "add to checkouts.cfg of buildout.coredev 4.3" in caplog.records[1].msg


def test_no_pr_commit_for_pre_commit_ci(caplog):
    payload = copy.deepcopy(PLONE_VERSION_PAYLOAD)
    payload["user"]["login"] = "pre-commit-ci[bot]"
    event = create_event({}, {}, payload=payload)
    caplog.set_level(logging.INFO)
    UpdateCoredevCheckouts(event)
    event.request.cleanup()

    assert len(caplog.records) == 1
    assert (
        "no commits on buildout.coredev as user pre-commit-ci[bot] is ignored"
        in caplog.records[0].msg
    )
