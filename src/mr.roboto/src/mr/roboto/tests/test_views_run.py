# -*- coding: utf-8 -*-
import unittest


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        from mr.roboto import main
        app = main({})
        from webtest import TestApp
        self.testapp = TestApp(app)

    def test_run_corecommit(self):
        res = self.testapp.get('/run/corecommit', status=200)
        self.failUnless('Pyramid' in res.body)
