# -*- coding: utf-8 -*-


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


class PullRequest(object):
    def __init__(self, pull_request, request):
        self.pull_request = pull_request
        self.request = request


class NewPullRequest(PullRequest):
    pass


class UpdatedPullRequest(PullRequest):
    pass


class MergedPullRequest(PullRequest):
    pass


class CommentOnPullRequest(object):
    def __init__(self, comment, pull_request, request):
        self.comment = comment
        self.pull_request = pull_request
        self.request = request
