from mr.roboto.subscriber import mail_to_cvs
from unittest import mock

import copy
import unittest


COMMIT = {
    "id": "4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8",
    "distinct": "true",
    "message": "[fc] Repository: plone.app.upgrade\nBranch: "
    "refs/heads/master\nDate: "
    "Files changed:\nM CHANGES.rst\nM setup.py",
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


class SubscribersTest(unittest.TestCase):
    def test_to_cvs_ignore(self):
        payload = {"commits": list(range(0, 50))}

        self.assertIsNone(mail_to_cvs(payload, ""))

    @mock.patch("requests.get")
    def test_to_cvs_send_email(self, mock_get):
        mock_get.content = mock.Mock(return_value="diff data")
        payload = {
            "commits": [copy.deepcopy(COMMIT)],
            "repository": {"name": "Products.CMFPlone"},
            "ref": "refs/heads/master",
        }

        mock_mail = mock.MagicMock()
        self.assertIsNone(mail_to_cvs(payload, mock_mail))

        self.assertTrue(mock_mail.send_immediately.called)

        mail = mock_mail.send_immediately.call_args[0][0]
        self.assertEqual(
            mail.subject, "Products.CMFPlone/master: [fc] Repository: plone.app.upgrade"
        )
        self.assertEqual(mail.sender, "mister-roboto <svn-changes@plone.org>")
        self.assertEqual(mail.recipients, ["plone-cvs@lists.sourceforge.net"])
