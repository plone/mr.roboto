from mr.roboto.utils import get_info_from_commit
from mr.roboto.utils import shorten_comment_url
from mr.roboto.utils import shorten_pull_request_url

from unittest import mock
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


class TestShortenPRUrls(unittest.TestCase):
    def test_shorten_url(self):
        url = 'https://github.com/plone/plone.app.registry/pull/20'
        self.assertEqual(shorten_pull_request_url(url), 'plone/plone.app.registry#20')

    def test_fallback(self):
        url = 'https://github.com/plone/random/url'
        self.assertEqual(shorten_pull_request_url(url), url)


class TestShortenCommentUrls(unittest.TestCase):
    def test_shorten_url(self):
        url = (
            'https://github.com/plone/plone.app.registry/pull/402#issuecomment-29038192'
        )
        self.assertEqual(
            shorten_comment_url(url), 'plone/plone.app.registry#402-29038192'
        )

    def test_fallback(self):
        url = 'https://github.com/plone/random/url'
        self.assertEqual(shorten_comment_url(url), url)

    def test_another_url(self):
        url = 'https://github.com/plone/plone.app.discussion/pull/147#issuecomment-461373454'
        self.assertEqual(
            shorten_comment_url(url), 'plone/plone.app.discussion#147-461373454'
        )


class TestGetInfoFromCommitTest(unittest.TestCase):
    @mock.patch('requests.get')
    def test_get_info_from_commit(self, mock_get):
        mock_get.content = mock.Mock(return_value='diff data')
        data = get_info_from_commit(COMMIT)
        self.assertEqual(data['files'], ['M last_commit.txt'])
        self.assertEqual(data['sha'], '4f7caf77eb1384572f4d7d9a90a4888fbcbd68a8')
        self.assertEqual(data['reply_to'], 'mister-roboto <mr.roboto@plone.org>')
        self.assertEqual(data['short_commit_msg'], '[fc] Repository: plone.app.upgrade')
        self.assertTrue(
            data['full_commit_msg'].endswith(
                'Files changed:\nM CHANGES.rst\nM setup.py'
            )
        )

    @mock.patch('requests.get')
    def test_unicode_on_messages(self, mock_get):
        mock_get.content = mock.Mock(return_value='diff data')
        commit_data = COMMIT
        commit_data['message'] = (
            'Höla què tal\n' 'Files changed:\nM CHÄNGES.rst\nM setup.py'
        )
        data = get_info_from_commit(commit_data)
        self.assertEqual(data['short_commit_msg'], 'Hla qu tal')
        self.assertTrue(
            data['full_commit_msg'].endswith('Files changed:\nM CHNGES.rst\nM setup.py')
        )
