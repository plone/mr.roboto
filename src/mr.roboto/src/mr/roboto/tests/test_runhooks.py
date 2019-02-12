# -*- coding: utf-8 -*-
from github.GithubException import GithubException
from mr.roboto import main
from webtest import TestApp

import mock
import unittest


class DummyHook(object):
    name = 'web'
    config = {'url': 'http://jenkins.plone.org/roboto/run/corecommit'}

    def delete(self):
        return


class DummyRepo(object):
    def __init__(self, name='Products.CMFPlone'):
        self.name = name

    def get_hooks(self):
        return [DummyHook()]

    def create_hook(self, *args, **kwargs):
        return


class DummyGetRepos(object):
    def get_repos(self):
        return [DummyRepo()]

    def get_repo(self, name):
        return DummyRepo(name)


class RunHooksTest(unittest.TestCase):
    def setUp(self):
        self.settings = {
            'plone_versions': '["4.3",]',
            'py3_versions': '["2.7", "3.6", ]',
            'github_users': '["mister-roboto", "jenkins-plone-org", ]',
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'xyz1234mnop',
            'sources_file': 'sources_pickle',
            'checkouts_file': 'checkouts_pickle',
            'github_user': 'x',
            'github_password': 'x',
            'collective_repos': '',
            'jenkins_url': 'https://jenkins.plone.org',
        }
        app = main({}, **self.settings)
        self.roboto = TestApp(app)

    def test_runhook_security(self):
        result = self.roboto.get('/run/githubcommithooks')
        self.assertIn('Token not active', result.ubody)

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_no_repo(self, m1):
        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertEqual(result.ubody, '"[]"')

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_no_web_hooks(self, m1):
        class DummyHook(object):
            name = 'not-web'

        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn('github Creating hooks on Products.CMFPlone', result.ubody)

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_exception(self, m1):
        class DummyHook(object):
            name = 'web'
            config = {'url': 'http://jenkins.plone.org/roboto/run/corecommit'}

        class DummyRepo(object):
            name = 'Products.CMFPlone'

            def get_hooks(self):
                return []

            def create_hook(self, *args, **kwargs):
                raise GithubException('one', 'two')

        class DummyGetRepos(object):
            def get_repos(self):
                return [DummyRepo()]

        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn('github Creating hooks on Products.CMFPlone', result.ubody)

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_web_hook_wrong_url(self, m1):
        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn('github Creating hooks on Products.CMFPlone', result.ubody)

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_web_hook_roboto_url(self, m1):
        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn('github Creating hooks on Products.CMFPlone', result.ubody)

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_debug(self, m1):
        self.roboto.app.registry.settings['debug'] = True

        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn('github Creating hooks on Products.CMFPlone', result.ubody)

    @mock.patch('github.MainClass.Github.get_organization')
    def test_runhook_collective(self, m1):
        self.roboto.app.registry.settings['collective_repos'] = 'repo1, repo2'
        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn('github Creating hooks on repo1', result.ubody)
        self.assertIn('github Creating hooks on repo2', result.ubody)
