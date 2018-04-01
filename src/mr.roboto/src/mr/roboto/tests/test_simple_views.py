# -*- coding: utf-8 -*-
from mr.roboto import main
from mr.roboto.views.home import parse_log_line
from webtest import TestApp

import mock
import os
import pickle
import unittest


class SimpleViewsTest(unittest.TestCase):

    def setUp(self):
        self.settings = {
            'plone_versions': '["4.3",]',
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'z',
            'sources_file': 'sources.pickle',
            'checkouts_file': 'checkouts.pickle',
            'github_user': 'x',
            'github_password': 'x',
        }
        app = main({}, **self.settings)
        self.roboto = TestApp(app)

    def clean_file(self, filename):
        try:
            os.remove(filename)
        except OSError:
            pass

    def test_home(self):
        result = self.roboto.get('/', status=200)
        self.assertIn(
            'Welcome to mr.roboto!',
            result.body,
        )

    def test_home_links(self):
        result = self.roboto.get('/', status=200)
        links = (
            'log?token',
            'sources.json',
            'checkouts.json',
            'update-sources-and-checkouts?token',
            'run/githubcommithooks?token',
        )
        for link in links:
            full_url = '{0}/{1}'.format(self.settings['roboto_url'], link)
            self.assertIn(
                full_url,
                result.body,
            )

    def test_log_view_unauthorized(self):
        result = self.roboto.get('/log')
        self.assertIn(
            'Token not active',
            result.body,
        )

    def test_log_view_no_file(self):
        filename = 'roboto.log'
        self.clean_file(filename)
        result = self.roboto.get(
            '/log?token={0}'.format(self.settings['api_key']),
        )
        self.assertIn(
            'File not found',
            result.body,
        )

    def test_log_view(self):
        filename = 'roboto.log'
        self.clean_file(filename)
        with open(filename, 'w') as log:
            log.write('log lines')

        result = self.roboto.get(
            '/log?token={0}'.format(self.settings['api_key']),
        )
        self.assertIn(
            'log lines',
            result.body,
        )
        self.clean_file(filename)

    def test_log_view_truncated(self):
        filename = 'roboto.log'
        self.clean_file(filename)
        with open(filename, 'w') as log:
            for number in range(0, 300):
                log.write('log line {0}\n'.format(number))

        result = self.roboto.get(
            '/log?token={0}'.format(self.settings['api_key']),
        )
        self.assertIn(
            'log line 250',
            result.body,
        )
        self.assertNotIn(
            'log line 50',
            result.body,
        )
        self.assertIn(
            '<pre>log line 299\n</pre><pre>log line 298\n</pre>',
            result.body,
        )
        self.clean_file(filename)

    def test_checkouts_file_no_file(self):
        filename = self.settings['checkouts_file']
        self.clean_file(filename)
        result = self.roboto.get('/checkouts.json')
        self.assertIn(
            'File not found',
            result.body,
        )

    def test_checkouts_file(self):
        filename = self.settings['checkouts_file']
        self.clean_file(filename)
        with open(filename, 'w') as checkouts:
            checkouts.write(pickle.dumps({'a_key': 'a value'}))

        result = self.roboto.get('/checkouts.json')
        self.assertIn(
            'a_key',
            result.body,
        )
        self.assertIn(
            'a value',
            result.body,
        )
        self.clean_file(filename)

    def test_sources_file_no_file(self):
        filename = self.settings['sources_file']
        self.clean_file(filename)
        result = self.roboto.get('/sources.json')
        self.assertIn(
            'File not found',
            result.body,
        )

    def test_sources_file(self):
        filename = self.settings['sources_file']
        self.clean_file(filename)
        data = {
            ('plone', 'Products.CMFPlone'): '5.1',
        }
        with open(filename, 'w') as sources:
            sources.write(pickle.dumps(data))

        result = self.roboto.get('/sources.json')
        self.assertIn(
            'plone/Products.CMFPlone',
            result.body,
        )
        self.assertIn(
            '5.1',
            result.body,
        )
        self.clean_file(filename)

    def test_update_pickles_security(self):
        result = self.roboto.get('/update-sources-and-checkouts')
        self.assertIn(
            'Token not active',
            result.body,
        )

    @mock.patch('mr.roboto.views.home.get_sources_and_checkouts')
    def test_update_pickles(self, m1):
        url = '/update-sources-and-checkouts?token={0}'.format(
            self.settings['api_key'],
        )
        result = self.roboto.get(url)
        self.assertIn(
            'updated!',
            result.body,
        )

    def test_no_changelog_view(self):
        result = self.roboto.get('/missing-changelog')
        self.assertIn(
            'add a change log entry',
            result.body,
        )

    def test_parse_log_line_no_format(self):
        self.assertEqual(
            parse_log_line('la la '),
            '<pre>la la </pre>',
        )

    def test_parse_log_line_format_other(self):
        msg = parse_log_line(
            '2016-05-16 23:45:00,343 INFO [mr.roboto][lala] my message',
        )

        self.assertIn(
            """<span class="timestamp">2016-05-16 23:45:00,343</span>""",
            msg,
        )
        self.assertIn(
            """<span class="info">INFO</span>""",
            msg,
        )
        self.assertIn(
            """<span class="message">my message</span>""",
            msg,
        )

    def test_parse_log_line_format_commit(self):
        msg = parse_log_line(
            '2013-12-12 22:34 INFO [mr.roboto][lala] '
            'Commit: on plone/ploneorg.core master '
            'fcbc0f2764f84a027766d96493ea0d40823f7ef1',
        )

        self.assertIn(
            """<span class="timestamp">2013-12-12 22:34</span>""",
            msg,
        )
        self.assertIn(
            """<span class="info">INFO</span>""",
            msg,
        )
        self.assertIn(
            '<span class="message">Commit: on plone/ploneorg.core master '
            '<a href="https://github.com/plone/ploneorg.core/commit/'
            'fcbc0f2764f84a027766d96493ea0d40823f7ef1">'
            'fcbc0f2764f84a027766d96493ea0d40823f7ef1</a></span>',
            msg,
        )

    def test_parse_log_line_format_commit_no_link(self):
        msg = parse_log_line(
            '2013-12-12 22:34 INFO [mr.roboto][lala] '
            'Commit: LETS COMMIT ON COREDEV',
        )

        self.assertIn(
            """<span class="timestamp">2013-12-12 22:34</span>""",
            msg,
        )
        self.assertIn(
            """<span class="info">INFO</span>""",
            msg,
        )
        self.assertIn(
            '<span class="message">Commit: LETS COMMIT ON COREDEV</span>',
            msg,
        )

    def test_parse_log_line_format_pull_request(self):
        msg = parse_log_line(
            '2013-11-10 12:15 WARN [mr.roboto][lala] '
            'PR plone/ploneorg.core#155: with action closed',
        )

        self.assertIn(
            """<span class="timestamp">2013-11-10 12:15</span>""",
            msg,
        )
        self.assertIn(
            """<span class="warn">WARN</span>""",
            msg,
        )
        self.assertIn(
            '<span class="message">PR <a href="https://github.com/plone/'
            'ploneorg.core/pull/155">plone/ploneorg.core#155</a>: '
            'with action closed</span>',
            msg,
        )
