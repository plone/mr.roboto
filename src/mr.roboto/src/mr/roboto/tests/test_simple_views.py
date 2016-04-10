# -*- coding: utf-8 -*-
from mr.roboto import main
from webtest import TestApp

import mock
import os
import pickle
import unittest


class SimpleViewsTest(unittest.TestCase):

    def setUp(self):
        self.settings = {
            'plone_versions': '["4.3",]',
            'roboto_url': 'http://jenkins.plone.org/roboto/',
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
            result.body
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
            full_url = '{0}{1}'.format(self.settings['roboto_url'], link)
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
            '/log?token={0}'.format(self.settings['api_key'])
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
            '/log?token={0}'.format(self.settings['api_key'])
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
            '/log?token={0}'.format(self.settings['api_key'])
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
            'log line 299\nlog line 298\n',
            result.body
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
            self.settings['api_key']
        )
        result = self.roboto.get(url)
        self.assertIn(
            'updated!',
            result.body,
        )
