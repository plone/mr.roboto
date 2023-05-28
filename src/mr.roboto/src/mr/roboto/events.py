class PullRequest:
    def __init__(self, pull_request, request):
        self.pull_request = pull_request
        self.request = request


class NewPullRequest(PullRequest):
    pass


class UpdatedPullRequest(PullRequest):
    pass


class MergedPullRequest(PullRequest):
    pass


class CommentOnPullRequest:
    def __init__(self, comment, pull_request, request):
        self.comment = comment
        self.pull_request = pull_request
        self.request = request
