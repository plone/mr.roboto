# -*- coding: utf-8 -*-
from git import Repo
from mr.roboto import main
from mr.roboto.buildout import PloneCoreBuildout
from tempfile import mkdtemp
from tempfile import NamedTemporaryFile
from webtest import TestApp as BaseApp

import os
import pickle
import shutil
import unittest


git_source = 'git://github.com/plone/Products'
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
        self.coredev_repo.create_head('4.3')
        self.coredev_repo.create_head('5.1')

        with NamedTemporaryFile(delete=False) as tmp_file:
            sources_pickle = tmp_file.name

        with NamedTemporaryFile(delete=False) as tmp_file:
            checkouts_pickle = tmp_file.name

        self.settings = {
            'plone_versions': '["5.1", "4.3", ]',
            'py3_versions': '["2.7", "3.6", ]',
            'plone_py3_versions': '["5.2", ]',
            'github_users': '["mister-roboto", "jenkins-plone-org", ]',
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'xyz1234mnop',
            'sources_file': sources_pickle,
            'checkouts_file': checkouts_pickle,
            'github_token': 'x',
        }
        app = main({}, **self.settings)
        self.roboto = BaseApp(app)

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

        self.assertEqual(data[('plone/Products.CMFPlone', 'master')], ['5.1', '4.3'])
        self.assertEqual(data[('plone/Products.CMFCore', '2.2.x')], ['5.1', '4.3'])

        with open(self.settings['checkouts_file'], 'br') as checkouts:
            data = pickle.load(checkouts)

        self.assertEqual(data['5.1'], ['plone.app.contenttypes', 'Products.CMFPlone'])
        self.assertEqual(data['4.3'], ['plone.app.contenttypes', 'Products.CMFPlone'])
