from github.GithubException import GithubException
from mr.roboto import main
from mr.roboto.tests import default_settings
from unittest import mock
from webtest import TestApp as BaseApp

import unittest


class DummyHook:
    name = "web"
    config = {"url": "http://jenkins.plone.org/roboto/run/corecommit"}

    def delete(self):
        return


class DummyRepo:
    def __init__(self, name="Products.CMFPlone"):
        self.name = name

    def get_hooks(self):
        return [DummyHook()]

    def create_hook(self, *args, **kwargs):
        return


class DummyGetRepos:
    def get_repos(self):
        return [DummyRepo()]

    def get_repo(self, name):
        return DummyRepo(name)


class RunHooksTest(unittest.TestCase):
    def setUp(self):
        override_settings = {"debug": "False"}
        app = main(
            {}, **default_settings(parsed=False, override_settings=override_settings)
        )
        self.roboto = BaseApp(app)
        self.settings = app.registry.settings

    def test_runhook_security(self):
        result = self.roboto.get("/run/githubcommithooks")
        self.assertIn("Token not active", result.ubody)

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_no_repo(self, m1):
        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertEqual(result.ubody, '"[]"')

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_no_web_hooks(self, m1):
        class DummyHook:
            name = "not-web"

        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn("github Creating hooks on Products.CMFPlone", result.ubody)

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_exception(self, m1):
        class DummyHook:
            name = "web"
            config = {"url": "http://jenkins.plone.org/roboto/run/corecommit"}

        class DummyRepo:
            name = "Products.CMFPlone"

            def get_hooks(self):
                return []

            def create_hook(self, *args, **kwargs):
                raise GithubException("one", "two", headers={})

        class DummyGetRepos:
            def get_repos(self):
                return [DummyRepo()]

        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn("github Creating hooks on Products.CMFPlone", result.ubody)

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_web_hook_wrong_url(self, m1):
        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn("github Creating hooks on Products.CMFPlone", result.ubody)

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_web_hook_roboto_url(self, m1):
        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn("github Creating hooks on Products.CMFPlone", result.ubody)

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_debug(self, m1):
        self.roboto.app.registry.settings["debug"] = True

        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn("github Creating hooks on Products.CMFPlone", result.ubody)

    @mock.patch("github.MainClass.Github.get_organization")
    def test_runhook_collective(self, m1):
        self.roboto.app.registry.settings["collective_repos"] = "repo1, repo2"
        m1.configure_mock(return_value=DummyGetRepos())

        url = f'/run/githubcommithooks?token={self.settings["api_key"]}'
        result = self.roboto.get(url)
        self.assertIn("github Creating hooks on repo1", result.ubody)
        self.assertIn("github Creating hooks on repo2", result.ubody)
