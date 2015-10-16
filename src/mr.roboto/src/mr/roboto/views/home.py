from mr.roboto.security import validatetoken
from pyramid.view import view_config

import logging
import pickle


log = logging.getLogger('HOME')


@view_config(route_name='home', renderer='mr.roboto:templates/home.pt')
def homePage(context, request):
    info = {}
    return dict(info=info)


@validatetoken
@view_config(route_name='log', renderer='mr.roboto:templates/log.pt')
def logPage(context, request):
    f = open('roboto.log', 'r')
    log = f.read()
    f.close()
    return dict(log=log)


@view_config(route_name='sources', renderer='json')
def sources(context, request):
    sources_file = request.registry.settings['sources_file']
    f = open(sources_file, 'r')
    d = pickle.load(f)
    output = {}
    for key, value in d.items():
        new_key = '%s/%s' % (key[0], key[1])
        output[new_key] = value
    return output


@view_config(route_name='checkouts', renderer='json')
def checkout(context, request):
    checkouts_file = request.registry.settings['checkouts_file']
    f = open(checkouts_file, 'r')
    d = pickle.load(f)
    return d
