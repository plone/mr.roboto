# -*- coding: utf-8 -*-
from pyramid.view import view_config

import os
import pickle


@view_config(route_name='home', renderer='mr.roboto:templates/home.pt')
def home_page(context, request):
    info = {}
    return dict(info=info)


@view_config(route_name='log', renderer='mr.roboto:templates/log.pt')
def log_page(context, request):
    filename = 'roboto.log'
    file_size = os.stat(filename).st_size

    token = request.token
    if token == request.registry.settings['api_key']:
        with open(filename) as f:
            log = f.read()
    else:
        log = 'Wrong/no token provided'
    return {
        'file_size': file_size,
        'log': log,
    }


@view_config(route_name='sources', renderer='json')
def sources(context, request):
    sources_file = request.registry.settings['sources_file']
    with open(sources_file) as f:
        data = pickle.load(f)
    output = {}
    for key, value in data.items():
        new_key = '{0}/{1}'.format(key[0], key[1])
        output[new_key] = value
    return output


@view_config(route_name='checkouts', renderer='json')
def checkout(context, request):
    checkouts_file = request.registry.settings['checkouts_file']
    with open(checkouts_file) as f:
        d = pickle.load(f)
    return d
