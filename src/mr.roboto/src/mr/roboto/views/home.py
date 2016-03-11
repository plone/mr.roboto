# -*- coding: utf-8 -*-
from mr.roboto.buildout import get_sources_and_checkouts
from mr.roboto.security import validate_request_token
from pyramid.view import view_config

import json
import os
import pickle


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
    file_size = os.stat(filename).st_size

    with open(filename) as f:
        log = f.read()

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


@view_config(route_name='update_pickles', renderer='json')
@validate_request_token
def update_pickles(context, request):
    get_sources_and_checkouts(request)
    return json.dumps({'message': 'updated!'})
