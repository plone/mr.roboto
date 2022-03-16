# -*- coding: utf-8 -*-
from git import Repo
from mr.roboto import main
from mr.roboto.buildout import PloneCoreBuildout
from mr.roboto.tests import default_settings
from tempfile import mkdtemp
from webtest import TestApp as BaseApp

import os
import pickle
import shutil
import unittest


git_source = 'https://github.com/plone/Products'
ssh_source = 'git@github.com:plone/Products'
SOURCES = """
[sources]
Products.CMFPlone = git {0}.CMFPlone.git pushurl={1}.CMFPlone.git branch=master
Products.CMFCore = git {0}.CMFCore.git pushurl={1}.CMFCore.git branch=2.2.x
Products.CMFDiff = git {0}.CMFDiff.git
""".format(
    git_source, ssh_source
)

CHECKOUTS = """
[buildout]
auto-checkout =
    plone.app.contenttypes
    Products.CMFPlone
"""


class BuildoutTest(unittest.TestCase):
    def setUp(self):
        self.coredev_repo = Repo.init(mkdtemp())
        PloneCoreBuildout.PLONE_COREDEV_LOCATION = (
            f'file://{self.coredev_repo.working_tree_dir}'
        )

        self._commit(SOURCES, filename='sources.cfg')
        self._commit(CHECKOUTS, filename='checkouts.cfg')

        app = main({}, **default_settings(parsed=False))
        self.roboto = BaseApp(app)
        self.settings = app.registry.settings

        for plone in self.settings['plone_versions']:
            self.coredev_repo.create_head(plone)

    def tearDown(self):
        shutil.rmtree(self.coredev_repo.working_tree_dir)
        os.remove(self.settings['sources_file'])
        os.remove(self.settings['checkouts_file'])

    def _commit(self, content='', filename='dummy'):
        dummy_file = os.path.join(self.coredev_repo.working_tree_dir, filename)
        with open(dummy_file, 'w') as afile:
            afile.write(content)
        self.coredev_repo.index.add([dummy_file])
        self.coredev_repo.index.commit('Random commit')

    def test_get_sources_and_checkouts(self):
        self.roboto.get(
            f'/update-sources-and-checkouts?token={self.settings["api_key"]}'
        )

        with open(self.settings['sources_file'], 'br') as sources:
            data = pickle.load(sources)

        self.assertEqual(data[('plone/Products.CMFPlone', 'master')], ['5.2', '6.0'])
        self.assertEqual(data[('plone/Products.CMFCore', '2.2.x')], ['5.2', '6.0'])

        with open(self.settings['checkouts_file'], 'br') as checkouts:
            data = pickle.load(checkouts)

        self.assertEqual(data['5.2'], ['plone.app.contenttypes', 'Products.CMFPlone'])
        self.assertEqual(data['6.0'], ['plone.app.contenttypes', 'Products.CMFPlone'])
