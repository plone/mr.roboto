# -*- encoding: utf-8 -*-
from hashlib import sha1
from pyramid.decorator import reify
from pyramid.request import Request

import hmac


def validate_github(fn):
    def wrapped(request):
        if 'X-Hub_Signature' in request.headers:
            sha1_gh = request.headers['X-Hub_Signature']
            hmac_value = hmac.new(
                request.registry.settings['api_key'].encode(),
                request.body,
                sha1,
            )
            sha1_compute = hmac_value.hexdigest()
            if sha1_gh == f'sha1={sha1_compute}':
                return fn(request)

        return {'success': False, 'message': 'Token not active'}

    return wrapped


def validate_service_token(fn):
    def wrapped(request):
        token = request.token
        if token == request.registry.settings['api_key']:
            return fn(request)

        return {'success': False, 'message': 'Token not active'}

    return wrapped


def validate_request_token(fn):
    def wrapped(context, request):
        token = request.token
        if token == request.registry.settings['api_key']:
            return fn(context, request)

        return {'success': False, 'message': 'Token not active'}

    return wrapped


class RequestWithAttributes(Request):

    @reify
    def token(self):
        if 'token' in self.GET:
            return self.GET['token']
