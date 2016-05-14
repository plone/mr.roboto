# -*- coding: utf-8 -*-
import pickle
import re


PULL_REQUEST_URL_RE = re.compile(r'https://github.com/.+/(.+)/pull/(\d+)')


def get_pickled_data(filename):
    return pickle.loads(open(filename).read())


def plone_versions_targeted(repo, branch, request):
    sources = get_pickled_data(request.registry.settings['sources_file'])
    try:
        return sources[(repo, branch)]
    except KeyError:
        return []


def shorten_pull_request_url(url):
    """Turn https://github.com/plone/plone.app.registry/pull/20 into
    plone.app.registry#20

    This way log messages can be easier to parse visually.

    Fallback to returning the full URL if the shortening does not work.
    """
    re_result = PULL_REQUEST_URL_RE.match(url)
    if re_result:
        return '{0}#{1}'.format(*re_result.groups())
    return url
