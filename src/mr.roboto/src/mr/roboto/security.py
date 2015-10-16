# -*- encoding: utf-8 -*-

from hashlib import sha1
from pyramid.decorator import reify
from pyramid.request import Request

import hmac


def validategithub(fn):
    def wrapped(request):
        if 'X-Hub_Signature' in request.headers:
            sha1_gh = request.headers['X-Hub_Signature']
            sha1_compute = hmac.new(request.registry.settings['api_key'], request.body, sha1).hexdigest()
            if sha1_gh == 'sha1=' + sha1_compute:
                return fn(request)
        else:
            return {'success': False, 'message': 'Token not active'}
    return wrapped


def validatetoken(fn):
    def wrapped(request):
        token = request.token
        if token == request.registry.settings['api_key']:
            return fn(request)
        else:
            return {'success': False, 'message': 'Token not active'}
    return wrapped


class RequestWithAttributes(Request):

    @reify
    def token(self):
        if 'token' in self.GET:
            return self.GET['token']

    @reify
    def core(self):
        return self.registry.settings['core']
