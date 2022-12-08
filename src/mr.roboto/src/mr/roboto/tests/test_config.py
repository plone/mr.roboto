from mr.roboto import main
from mr.roboto.tests import default_settings
from webtest import TestApp as BaseApp

import unittest


class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        app = main({}, **default_settings(parsed=False))
        self.roboto = BaseApp(app)
        self.settings = app.registry.settings

    def test_plone_versions(self):
        self.assertEqual(self.settings['plone_versions'], ['5.2', '6.0'])

    def test_python_versions(self):
        self.assertEqual(
            self.settings['py_versions'], {'5.2': ['2.7', '3.6'], '6.0': ['3.8', '3.9']}
        )

    def test_github_users(self):
        self.assertEqual(
            self.settings['github_users'], ['mister-roboto', 'jenkins-plone-org']
        )

    def test_roboto_url(self):
        self.assertEqual(self.settings['roboto_url'], 'http://jenkins.plone.org/roboto')

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
            'py_versions': '["2.7", "3.6", ]',
            'github_users': '["mister-roboto", "jenkins-plone-org", ]',
            'roboto_url': 'x',
            'api_key': 'x',
            'sources_file': 'x',
            'checkouts_file': 'x',
            'github_token': 'x',
        }
        app = main({}, **settings)
        roboto = BaseApp(app)
        settings = roboto.app.registry.settings
        self.assertFalse(settings['debug'])
