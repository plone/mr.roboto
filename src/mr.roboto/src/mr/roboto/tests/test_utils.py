# -*- coding: utf-8 -*-
from mr.roboto.utils import shorten_pull_request_url

import unittest


class TestShortenPRUrls(unittest.TestCase):

    def test_shorten_url(self):
        url = 'https://github.com/plone/plone.app.registry/pull/20'
        self.assertEqual(
            shorten_pull_request_url(url),
            'plone/plone.app.registry#20'
        )

    def test_fallback(self):
        url = 'https://github.com/plone/random/url'
        self.assertEqual(
            shorten_pull_request_url(url),
            url
        )
