from hashlib import sha1
from mr.roboto.tests import minimal_main
from mr.roboto.views.runcorejob import get_pickled_data
from mr.roboto.views.runcorejob import get_user
from tempfile import NamedTemporaryFile
from unittest import mock
from webtest import TestApp as BaseApp

import copy
import hmac
import json
import os
import pickle
import unittest
import urllib


"""
Reduced set of data sent by Github when a commit is made on a repository.

Each payload is adapted later on to test all corner cases.
"""
COREDEV_COMMIT_PAYLOAD = {
    "ref": "refs/heads/master",
    "commits": [
        {
            "id": "4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8",
            "message": "[fc] Repository: plone.app.upgrade\nBranch: "
            "refs/heads/master\nDate: ",
            "timestamp": "2016-03-31T21:44:15+02:00",
            "url": "https://github.com/plone/buildout.coredev/commit"
            "/4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8",
            "author": {
                "name": "mister-roboto",
                "email": "mr.roboto@plone.org",
                "username": "mister-roboto",
            },
            "committer": {
                "name": "mister-roboto",
                "email": "mr.roboto@plone.org",
                "username": "mister-roboto",
            },
            "added": [],
            "removed": [],
            "modified": ["last_commit.txt"],
        }
    ],
    "repository": {
        "name": "buildout.coredev",
        "full_name": "plone/buildout.coredev",
        "organization": "plone",
    },
    "pusher": {"name": "mister-roboto", "email": "mr.roboto@plone.org"},
}

PACKAGE_COMMIT_PAYLOAD = copy.deepcopy(COREDEV_COMMIT_PAYLOAD)
PACKAGE_COMMIT_PAYLOAD["repository"]["name"] = "Products.CMFPlone"
PACKAGE_COMMIT_PAYLOAD["repository"]["full_name"] = "plone/Products.CMFPlone"


"""
Sample data returned by mr.roboto.subscriber.get_info_from_commit for all
different use cases that need to be tested.
"""
SAMPLE_DATA = {
    "files": ["M CHANGES.rst", "M setup.py"],
    "short_commit_msg": "Random commit",
    "full_commit_msg": "Random commit\n\nLonger explanation",
    "diff": "+ something added\n- something removed\n",
    "reply_to": "Plone contributor <contributor@plone.org>",
}

SAMPLE_DATA_FAKE = {
    "files": ["M CHANGES.rst", "M setup.py"],
    "short_commit_msg": "[fc] Repository: mockup",
    "full_commit_msg": "[fc] Repository: mockup\n\nBranch: refs/heads/master",
    "diff": "+ something added\n- something removed\n",
    "reply_to": "Plone contributor <contributor@plone.org>",
}

SAMPLE_DATA_CI_SKIP = {
    "files": ["M CHANGES.rst", "M setup.py"],
    "short_commit_msg": "Back to development: 1.3.25",
    "full_commit_msg": "Back to development: 1.3.25\n[ci skip]",
    "diff": "+ something added\n- something removed\n",
    "reply_to": "Plone contributor <contributor@plone.org>",
}

SAMPLE_DATA_SOURCES = {
    "files": ["M sources.cfg", "M setup.py"],
    "short_commit_msg": "Back to development: 1.3.25",
    "full_commit_msg": "Back to development: 1.3.25\n[",
    "diff": "+ something added\n- something removed\n",
    "reply_to": "Plone contributor <contributor@plone.org>",
}

GET_INFO = "mr.roboto.views.runcorejob.get_info_from_commit"


class RunCoreJobTest(unittest.TestCase):
    def setUp(self):
        settings = {}
        app = minimal_main(settings, "mr.roboto.views.runcorejob")
        self.roboto = BaseApp(app)
        self.settings = app.registry.settings

    def tearDown(self):
        if os.path.exists(self.settings["checkouts_file"]):
            os.remove(self.settings["checkouts_file"])
        if os.path.exists(self.settings["sources_file"]):
            os.remove(self.settings["sources_file"])

    def populate_sources_and_checkouts(self, sources_data, checkouts_data):
        with NamedTemporaryFile(delete=False) as tmp_file:
            sources_pickle = tmp_file.name
            with open(sources_pickle, "bw") as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(sources_data))

        with NamedTemporaryFile(delete=False) as tmp_file:
            checkouts_pickle = tmp_file.name
            with open(checkouts_pickle, "bw") as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(checkouts_data))

        settings = {
            "sources_file": sources_pickle,
            "checkouts_file": checkouts_pickle,
        }
        app = minimal_main(settings, "mr.roboto.views.runcorejob")
        self.roboto = BaseApp(app)
        self.settings = app.registry.settings

    def prepare_data(self, payload):
        body = urllib.parse.urlencode({"payload": json.dumps(payload)})
        hmac_value = hmac.new(self.settings["api_key"].encode(), body.encode(), sha1)
        digest = hmac_value.hexdigest()
        return digest, body

    def call_view(self, payload):
        digest, body = self.prepare_data(payload)
        result = self.roboto.post(
            "/run/corecommit",
            headers={"X-Hub_Signature": f"sha1={digest}"},
            params=body,
        )
        return result

    def test_no_validation(self):
        res = self.roboto.post("/run/corecommit")
        self.assertIn("Token not active", res.ubody)

    def test_ping_answer(self):
        result = self.call_view({"ping": "true"})

        self.assertIn("pong", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA)
    def test_commit_to_coredev(self, m1):
        self.populate_sources_and_checkouts(
            sources_data={("plone/plone.app.discussion", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(COREDEV_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Commit to coredev, nothing to do", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA_FAKE)
    def test_fake_commit_to_coredev(self, m1):
        self.populate_sources_and_checkouts(
            sources_data={("plone/plone.app.discussion", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(COREDEV_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Commit to coredev, nothing to do", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA_CI_SKIP)
    def test_ci_skip_commit_to_coredev(self, m1):
        self.populate_sources_and_checkouts(
            sources_data={("plone/plone.app.discussion", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(COREDEV_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Commit to coredev, nothing to do", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA_SOURCES)
    @mock.patch("mr.roboto.views.runcorejob.get_sources_and_checkouts")
    def test_sources_changed_commit_to_coredev(self, m1, m2):
        self.populate_sources_and_checkouts(
            sources_data={("plone/plone.app.discussion", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(COREDEV_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Commit to coredev, nothing to do", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA_CI_SKIP)
    def test_ci_skip_non_coredev_commit(self, m1):
        self.populate_sources_and_checkouts(
            sources_data={("plone/plone.app.discussion", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(PACKAGE_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Skipping CI", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA)
    def test_branch_not_in_sources_commit(self, m1):
        self.populate_sources_and_checkouts(
            sources_data={("plone/plone.app.discussion", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(PACKAGE_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Commits done on a branch, nothing to do", result.ubody)

    @mock.patch(GET_INFO, return_value=SAMPLE_DATA)
    @mock.patch("mr.roboto.views.runcorejob.commit_to_coredev")
    def test_branch_in_sources_commit(self, m1, m2):
        self.populate_sources_and_checkouts(
            sources_data={("plone/Products.CMFPlone", "master"): ["5.1"]},
            checkouts_data={"5.1": ["plone.app.upgrade"]},
        )
        result = self.call_view(PACKAGE_COMMIT_PAYLOAD)

        self.assertIn("Thanks! Plone Jenkins CI will run tests", result.ubody)


class AuxiliaryFunctionsTest(unittest.TestCase):
    def test_get_user_none(self):
        self.assertEqual(get_user({"name": "none"}), "NoBody <nobody@plone.org>")

    def test_get_user(self):
        self.assertEqual(
            get_user({"name": "jon", "email": "jon@plone.org"}), "jon <jon@plone.org>"
        )

    def test_load_data(self):
        data = "test string"
        with NamedTemporaryFile(delete=False) as tmp_file:
            filename = tmp_file.name
            with open(filename, "bw") as tmp_file_writer:
                tmp_file_writer.write(pickle.dumps(data))

        self.assertEqual(get_pickled_data(filename), data)
        os.remove(filename)
