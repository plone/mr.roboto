

class NewCoreDevPush(object):
    def __init__(self, payload, request):
        self.payload = payload
        self.request = request


class CommitAndMissingCheckout(object):
    def __init__(self, who, request, repo, branch, pv, email):
        self.who = who
        self.request = request
        self.repo = repo
        self.branch = branch
        self.pv = pv
        self.email = email