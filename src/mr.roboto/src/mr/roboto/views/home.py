from pyramid.view import view_config

import logging

log = logging.getLogger('HOME')


@view_config(route_name='home', renderer='mr.roboto:templates/home.pt')
def homePage(context, request):
    info = {}
    return dict(info=info)



