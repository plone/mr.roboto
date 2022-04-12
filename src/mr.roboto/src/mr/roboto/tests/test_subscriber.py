# -*- coding: utf-8 -*-
from mr.roboto.subscriber import mail_missing_checkout
from mr.roboto.subscriber import mail_to_cvs

import copy
import mock
import unittest


COMMIT = {
    'id': '4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8',
    'distinct': 'true',
    'message': '[fc] Repository: plone.app.upgrade\nBranch: '
    'refs/heads/master\nDate: '
    'Files changed:\nM CHANGES.rst\nM setup.py',
    'timestamp': '2016-03-31T21:44:15+02:00',
    'url': 'https://github.com/plone/buildout.coredev/commit'
    '/4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8',
    'author': {
        'name': 'mister-roboto',
        'email': 'mr.roboto@plone.org',
        'username': 'mister-roboto',
    },
    'committer': {
        'name': 'mister-roboto',
        'email': 'mr.roboto@plone.org',
        'username': 'mister-roboto',
    },
    'added': [],
    'removed': [],
    'modified': ['last_commit.txt'],
}


class SubscribersTest(unittest.TestCase):
    def test_mail_missing_checkout(self):
        mock_mail = mock.MagicMock()
        mail_missing_checkout(
            mock_mail,
            'mister-roboto <roboto@plone.org>',
            'plone/Products.CMFPlone',
            'master',
            '5.1',
            'roboto@plone.org',
        )
        self.assertTrue(mock_mail.send_immediately.called)

        mail = mock_mail.send_immediately.call_args[0][0]
        self.assertEqual(
            mail.subject, 'POSSIBLE CHECKOUT ERROR plone/Products.CMFPlone master'
        )
        self.assertEqual(mail.sender, 'Jenkins Job FAIL <jenkins@plone.org>')
        self.assertEqual(
            mail.recipients,
            ['roboto@plone.org'],
        )

    def test_to_cvs_ignore(self):
        payload = {'commits': [x for x in range(0, 50)]}

        self.assertIsNone(mail_to_cvs(payload, ''))

    @mock.patch('requests.get')
    def test_to_cvs_send_email(self, mock_get):
        mock_get.content = mock.Mock(return_value='diff data')
        payload = {
            'commits': [copy.deepcopy(COMMIT)],
            'repository': {'name': 'Products.CMFPlone'},
            'ref': 'refs/heads/master',
        }

        mock_mail = mock.MagicMock()
        self.assertIsNone(mail_to_cvs(payload, mock_mail))

        self.assertTrue(mock_mail.send_immediately.called)

        mail = mock_mail.send_immediately.call_args[0][0]
        self.assertEqual(
            mail.subject, 'Products.CMFPlone/master: [fc] Repository: plone.app.upgrade'
        )
        self.assertEqual(mail.sender, 'mister-roboto <svn-changes@plone.org>')
        self.assertEqual(mail.recipients, ['plone-cvs@lists.sourceforge.net'])
