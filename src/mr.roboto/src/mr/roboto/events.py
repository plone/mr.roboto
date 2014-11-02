
class NewCoreDevBuildoutPush(object):
    def __init__(self, payload, request):
        self.payload = payload
        self.request = request


class NewCoreDevPush(object):
    def __init__(self, payload, request):
        self.payload = payload
        self.request = request


class KGSJobSuccess(object):
    def __init__(self, payload, request, result):
        self.payload = payload
        self.request = request
        self.result = result


class KGSJobFailure(object):
    def __init__(self, payload, request, result):
        self.payload = payload
        self.request = request
        self.result = result
