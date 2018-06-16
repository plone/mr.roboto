# -*- coding: utf-8 -*-
import pickle
import re
import requests


PULL_REQUEST_URL_RE = re.compile(r'https://github.com/(.+/.+)/pull/(\d+)')


def get_pickled_data(filename):
    return pickle.loads(open(filename, 'br').read())


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


def get_info_from_commit(commit):
    diff = requests.get(commit['url'] + '.diff').content

    files = ['A {0}'.format(f) for f in commit['added']]
    files.extend('M {0}'.format(f) for f in commit['modified'])
    files.extend('D {0}'.format(f) for f in commit['removed'])

    encoded_message = commit['message'].encode('ascii', 'ignore').decode()
    short_commit_msg = encoded_message.split('\n')[0][:60]
    reply_to = '{0} <{1}>'.format(
        commit['committer']['name'],
        commit['committer']['email'],
    )

    return {
        'diff': diff,
        'files': files,
        'short_commit_msg': short_commit_msg,
        'full_commit_msg': encoded_message,
        'reply_to': reply_to,
        'sha': commit['id'],
    }
