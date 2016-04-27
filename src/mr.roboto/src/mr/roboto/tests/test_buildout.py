# -*- coding: utf-8 -*-
from git import Repo
from mr.roboto import main
from mr.roboto.buildout import PloneCoreBuildout
from tempfile import mkdtemp
from tempfile import NamedTemporaryFile
from webtest import TestApp

import os
import pickle
import shutil
import unittest


SOURCES = """
[sources]
Products.CMFPlone = git git://github.com/plone/Products.CMFPlone.git pushurl=git@github.com:plone/Products.CMFPlone.git branch=master
Products.CMFCore = git git://github.com/plone/Products.CMFCore.git pushurl=git@github.com:plone/Products.CMFCore.git branch=2.2.x
Products.CMFDiff = git git://github.com/plone/Products.CMFDiff.git
"""

CHECKOUTS = """
[buildout]
auto-checkout =
    plone.app.contenttypes
    Products.CMFPlone
"""


class BuildoutTest(unittest.TestCase):

    def setUp(self):
        self.coredev_repo = Repo.init(mkdtemp())
        PloneCoreBuildout.PLONE_COREDEV_LOCATION = 'file://{0}'.format(
            self.coredev_repo.working_tree_dir,
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
            'roboto_url': 'http://jenkins.plone.org/roboto',
            'api_key': 'xyz1234mnop',
            'sources_file': sources_pickle,
            'checkouts_file': checkouts_pickle,
            'github_user': 'x',
            'github_password': 'x',
        }
        app = main({}, **self.settings)
        self.roboto = TestApp(app)

    def tearDown(self):
        shutil.rmtree(self.coredev_repo.working_tree_dir)
        os.remove(self.settings['sources_file'])
        os.remove(self.settings['checkouts_file'])

    def _commit(self, content='', filename='dummy'):
        dummy_file = os.path.join(self.coredev_repo.working_tree_dir, filename)
        with open(dummy_file, 'w') as afile:
            afile.write(content)
        self.coredev_repo.index.add([dummy_file, ])
        self.coredev_repo.index.commit('Random commit')

    def test_get_sources_and_checkouts(self):
        self.roboto.get(
            '/update-sources-and-checkouts?token={0}'.format(
                self.settings['api_key']
            ),
        )

        with open(self.settings['sources_file']) as sources:
            data = pickle.load(sources)

        self.assertEqual(
            data[('plone/Products.CMFPlone', 'master')],
            ['5.1', '4.3', ]
        )
        self.assertEqual(
            data[('plone/Products.CMFCore', '2.2.x')],
            ['5.1', '4.3', ]
        )

        with open(self.settings['checkouts_file']) as checkouts:
            data = pickle.load(checkouts)

        self.assertEqual(
            data['5.1'],
            ['plone.app.contenttypes', 'Products.CMFPlone', ]
        )
        self.assertEqual(
            data['4.3'],
            ['plone.app.contenttypes', 'Products.CMFPlone', ]
        )
