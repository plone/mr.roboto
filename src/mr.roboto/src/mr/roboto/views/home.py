from pyramid.view import view_config

from mr.roboto.security import validatetoken

import logging

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



