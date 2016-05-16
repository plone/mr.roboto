# -*- coding: utf-8 -*-
from collections import deque
from mr.roboto.buildout import get_sources_and_checkouts
from mr.roboto.security import validate_request_token
from pyramid.view import view_config

import json
import os
import pickle
import re


LOG_LINE_RE = re.compile(
    r'([\d\-\s:,]+)'  # timestamp
    r'(\w+)'  # log level
    r'\s+'  # space
    r'\[[\w\.]+\]\[\w+\]'  # logger name ([mr.roboto][waitress]
    r'(.+)'  # message
)

PULL_REQUEST_LOG_MSG_RE = re.compile(
    r'PR\s+'
    '(\S+)'  # repo/package.name.this
    '#'
    '(\d+)'  # pull request number
)

COMMIT_LOG_MSG_RE = re.compile(
    r'\s+(\S+)'  # repo/package.name
    r'\s+\S+'  # branch name
    r'\s+(\w+)$'  # commit hash at the end of the line
)

PULL_REQUEST_URL = '<a href="https://github.com/{1}/pull/{2}">{0}</a>'
COMMIT_URL = '<a href="https://github.com/{0}/commit/{1}">{1}</a>'

LOG_LINE = """<span class="timestamp">{timestamp}</span>
<span class="{LEVEL}">{level}</span>
<span class="message">{msg}</span>
<br/>"""


def parse_log_line(log_line):
    line_parsed = LOG_LINE_RE.match(log_line)
    if line_parsed:
        groups = line_parsed.groups()
        msg = groups[2]
        pull_request_log = PULL_REQUEST_LOG_MSG_RE.search(msg)
        if pull_request_log:
            pull_request_groups = pull_request_log.groups()
            text = '{0}#{1}'.format(*pull_request_groups)
            msg = msg.replace(
                text,
                PULL_REQUEST_URL.format(text, *pull_request_groups)
            )
        else:
            commit_log = COMMIT_LOG_MSG_RE.search(msg)
            if commit_log:
                commit_log_groups = commit_log.groups()
                msg = msg.replace(
                    commit_log_groups[1],
                    COMMIT_URL.format(*commit_log_groups)
                )

        return LOG_LINE.format(**{
            'timestamp': groups[0].strip(),
            'level': groups[1].strip(),
            'LEVEL': groups[1].lower().strip(),
            'msg': msg.strip(),
        })
    else:
        return log_line


@view_config(route_name='home', renderer='mr.roboto:templates/home.pt')
def home_page(context, request):
    info = {
        'roboto_url': request.registry.settings['roboto_url']
    }
    return dict(info=info)


@view_config(route_name='log', renderer='mr.roboto:templates/log.pt')
@validate_request_token
def log_page(context, request):
    filename = 'roboto.log'
    try:
        file_size = os.stat(filename).st_size
        with open(filename) as log_file:
            raw_data = deque(log_file, maxlen=200)
            raw_data.reverse()
            log = ''.join([parse_log_line(l) for l in raw_data])
    except OSError:
        return {
            'success': False,
            'message': 'File not found',
        }

    return {
        'success': True,
        'file_size': file_size,
        'log': log,
    }


@view_config(route_name='sources', renderer='json')
def sources(context, request):
    sources_file = request.registry.settings['sources_file']
    try:
        with open(sources_file) as f:
            data = pickle.load(f)
    except IOError:
        return {
            'success': False,
            'message': 'File not found',
        }
    output = {}
    for key, value in data.items():
        new_key = '{0}/{1}'.format(key[0], key[1])
        output[new_key] = value
    return output


@view_config(route_name='checkouts', renderer='json')
def checkout(context, request):
    checkouts_file = request.registry.settings['checkouts_file']
    try:
        with open(checkouts_file) as checkouts:
            data = pickle.load(checkouts)
    except IOError:
        return {
            'success': False,
            'message': 'File not found',
        }
    return data


@view_config(route_name='update_pickles', renderer='json')
@validate_request_token
def update_pickles(context, request):
    get_sources_and_checkouts(request)
    return json.dumps({'message': 'updated!'})


@view_config(
    route_name='missing_changelog',
    renderer='mr.roboto:templates/missing_changelog.pt'
)
def missing_changelog(context, request):
    return {}
