# -*- coding: utf-8 -*-
from mr.roboto import main
from webtest import TestApp

import unittest


class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        settings = {
            'plone_versions': '["4.3", "5.1"]',
            'py3_versions': '["2.7", "3.6", ]',
            'github_users': '["mister-roboto", "jenkins-plone-org", ]',
            'roboto_url': 'http://mr.roboto.plone.org',
            'api_key': '1234567890',
            'sources_file': 'sources.pickle',
            'checkouts_file': 'checkouts.pickle',
            'github_user': 'gh_user',
            'github_password': 'secret',
            'debug': 'True',
        }
        app = main({}, **settings)
        self.roboto = TestApp(app)
        self.settings = self.roboto.app.registry.settings

    def test_plone_versions(self):
        self.assertEqual(self.settings['plone_versions'], ['4.3', '5.1'])

    def test_py3_versions(self):
        self.assertEqual(self.settings['py3_versions'], ['2.7', '3.6'])

    def test_github_users(self):
        self.assertEqual(
            self.settings['github_users'], ['mister-roboto', 'jenkins-plone-org']
        )

    def test_roboto_url(self):
        self.assertEqual(self.settings['roboto_url'], 'http://mr.roboto.plone.org')

    def test_api_key(self):
        self.assertEqual(self.settings['api_key'], '1234567890')

    def test_sources_file(self):
        self.assertEqual(self.settings['sources_file'], 'sources.pickle')

    def test_checkouts_file(self):
        self.assertEqual(self.settings['checkouts_file'], 'checkouts.pickle')

    def test_debug(self):
        self.assertTrue(self.settings['debug'])

    def test_no_debug(self):
        settings = {
            'plone_versions': '["4.3", "5.1"]',
            'py3_versions': '["2.7", "3.6", ]',
            'github_users': '["mister-roboto", "jenkins-plone-org", ]',
            'roboto_url': 'x',
            'api_key': 'x',
            'sources_file': 'x',
            'checkouts_file': 'x',
            'github_user': 'x',
            'github_password': 'x',
        }
        app = main({}, **settings)
        roboto = TestApp(app)
        settings = roboto.app.registry.settings
        self.assertFalse(settings['debug'])
