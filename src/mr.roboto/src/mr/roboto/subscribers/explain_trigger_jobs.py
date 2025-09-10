from .base import IGNORE_NO_JENKINS
from .base import PullRequestSubscriber
from mr.roboto.events import NewPullRequest
from mr.roboto.utils import plone_versions_targeted
from pyramid.events import subscriber

import logging


logger = logging.getLogger()


@subscriber(NewPullRequest)
class ExplainHowToTriggerJenkinsJobs(PullRequestSubscriber):
    """
    The comment automatically added to new Plone project PRs.
    """

    def run(self):
        """
        Add the comment when a new Plone project PR is created.
        """
        if self.repo_name in IGNORE_NO_JENKINS:
            return

        plone_versions = plone_versions_targeted(
            self.repo_full_name, self.target_branch, self.event.request
        )
        if not plone_versions:
            return

        user = self.pull_request["user"]["login"]
        msg = (
            f"@{user} thanks for creating this Pull Request and helping to improve "
            "Plone!\n"
            "\n"
            "TL;DR: Finish pushing changes, pass all other checks, "
            "then paste a comment:\n"
            "```\n"
            "@jenkins-plone-org please run jobs\n"
            "```\n"
            "\n"
            "To ensure that these changes do not break other parts of Plone, the Plone "
            "test suite matrix needs to pass, but it takes 30-60 min.  "
            "Other CI checks are usually much faster and the Plone Jenkins resources "
            "are limited, so when done pushing changes and all other checks pass "
            "either [start all Jenkins PR jobs yourself]"
            "(https://jenkinsploneorg.readthedocs.io/en/latest/"
            "run-pull-request-jobs.html#run-a-pull-request-job), "
            "or simply add the comment above in this PR to start all the jobs "
            "automatically.\n"
            "\n"
            "Happy hacking!"
        )
        self.g_issue.create_comment(body=msg)
