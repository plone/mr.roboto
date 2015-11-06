# -*- coding: utf-8 -*-
from mr.roboto.security import validate_token
from pyramid.view import view_config

import logging
import pickle


log = logging.getLogger('HOME')


@view_config(route_name='home', renderer='mr.roboto:templates/home.pt')
def home_page(context, request):
    info = {}
    return dict(info=info)


@validate_token
@view_config(route_name='log', renderer='mr.roboto:templates/log.pt')
def log_page(context, request):
    with open('roboto.log') as f:
        log = f.read()
    return dict(log=log)


@view_config(route_name='sources', renderer='json')
def sources(context, request):
    sources_file = request.registry.settings['sources_file']
    with open(sources_file) as f:
        d = pickle.load(f)
    output = {}
    for key, value in d.items():
        new_key = '{0}/{1}'.format(key[0], key[1])
        output[new_key] = value
    return output


@view_config(route_name='checkouts', renderer='json')
def checkout(context, request):
    checkouts_file = request.registry.settings['checkouts_file']
    with open(checkouts_file) as f:
        d = pickle.load(f)
    return d
