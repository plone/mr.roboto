# -*- coding: utf-8 -*-
from mr.roboto.subscriber import get_info_from_commit

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
        'username': 'mister-roboto'
    },
    'committer': {
        'name': 'mister-roboto',
        'email': 'mr.roboto@plone.org',
        'username': 'mister-roboto'
    },
    'added': [],
    'removed': [],
    'modified': ['last_commit.txt', ]
}


class RunCoreJobTest(unittest.TestCase):

    @mock.patch('requests.get')
    def test_get_info_from_commit(self, mock_get):
        mock_get.content = mock.Mock(return_value='diff data')
        data = get_info_from_commit(COMMIT)
        self.assertEqual(
            data['files'],
            ['M last_commit.txt', ],
        )
        self.assertEqual(
            data['sha'],
            '4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8',
        )
        self.assertEqual(
            data['reply_to'],
            'mister-roboto <mr.roboto@plone.org>',
        )
        self.assertEqual(
            data['short_commit_msg'],
            '[fc] Repository: plone.app.upgrade',
        )
        self.assertTrue(
            data['full_commit_msg'].endswith(
                'Files changed:\nM CHANGES.rst\nM setup.py'
            )
        )
