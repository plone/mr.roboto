# -*- encoding: utf-8 -*-
""" Core repos services.
"""
import json
from webob import Response, exc
from cornice import Service

core = Service(name='core', path='/core', description="Core services")

kgs = Service(name='kgs', path='/kgs', description="Known Good code-dev")


class _401(exc.HTTPError):
    def __init__(self, msg='Unauthorized'):
        body = {'status': 401, 'message': msg}
        Response.__init__(self, json.dumps(body))
        self.status = 401
        self.content_type = 'application/json'


def valid_token(request):
    header = 'X-Messaging-Token'
    token = request.headers.get(header)
    if token is None:
        raise _401()

    if token != request.registry.settings['api_key']:
        raise _401()
    request.validated['auth'] = True


def valid_core(request):
    try:
        core = json.loads(request.body)
    except ValueError:
        request.errors.add('body', 'core', 'Not valid JSON')
        return

    # make sure we have the fields we want
    if 'repo' not in core:
        request.errors.add('body', 'repo', 'Missing repo')
        return

    if 'egg' not in core:
        request.errors.add('body', 'egg', 'Missing egg')
        return
    request.validated['core'] = core


@core.get()
def getCorePackages(request):
    """all the repos added"""
    return request.core.get()


@core.post(validators=(valid_token, valid_core))
def postNewCorePackage(request):
    """adds a repo"""
    request.core.add(request.validated['core']['egg'], request.validated['core']['repo'])
    # TODO Add the needed triggers on the GitHub on push and commit
    # it must call the /run/corecommit with a parameter

    return {'status': 'added'}



@kgs.get()
def getKGSPackages(request):
    """Returns de last KGS from core-dev
    """
    pass
