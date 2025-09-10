from .base import IGNORE_NO_TEST_NEEDED
from mr.roboto.events import CommentOnPullRequest
from mr.roboto.utils import plone_versions_targeted
from mr.roboto.utils import shorten_comment_url
from pyramid.events import subscriber

import logging
import requests


logger = logging.getLogger()


@subscriber(CommentOnPullRequest)
class TriggerPullRequestJenkinsJobs:
    def __init__(self, event):
        self.event = event

        self.run()

    @property
    def short_url(self):
        return shorten_comment_url(self.event.comment["html_url"])

    def log(self, msg, level="info"):
        if level == "warn":
            logger.warning(f"COMMENT {self.short_url}: {msg}")
            return
        logger.info(f"COMMENT {self.short_url}: {msg}")

    def run(self):
        if self._should_trigger_jobs():
            plone_versions = self._which_plone_versions()
            self._trigger_jobs(plone_versions)

    def _should_trigger_jobs(self):
        pull_request_url = self.event.pull_request["html_url"]
        repo_name = pull_request_url.split("/")[-3]
        if repo_name in IGNORE_NO_TEST_NEEDED:
            self.log("skip triggering jenkins jobs, repo is ignored")
            return False

        return "@jenkins-plone-org please run jobs" in self.event.comment["body"]

    def _which_plone_versions(self):
        response = requests.get(self.event.pull_request["url"])
        if response.status_code != 200:
            self.log("Could not get information regarding pull request", level="warn")
            return []

        data = response.json()
        target_branch = data["base"]["ref"]
        repo_full_name = data["base"]["repo"]["full_name"]

        plone_versions = plone_versions_targeted(
            repo_full_name, target_branch, self.event.request
        )

        tracked_versions = self.event.request.registry.settings["plone_versions"]
        if (
            repo_full_name == "plone/buildout.coredev"
            and target_branch in tracked_versions
        ):
            plone_versions = (target_branch,)

        elif not plone_versions:
            self.log("Does not target any Plone version")

        return plone_versions

    def _trigger_jobs(self, plone_versions):
        settings = self.event.request.registry.settings
        python_versions = settings["py_versions"]

        for plone in plone_versions:
            for python in python_versions[plone]:
                self._create_job(f"{plone}-{python}")

    def _create_job(self, version):
        settings = self.event.request.registry.settings
        jenkins_user = settings["jenkins_user_id"]
        jenkins_token = settings["jenkins_user_token"]
        pull_request_url = self.event.pull_request["html_url"]

        requests.post(
            f"https://jenkins.plone.org/job/pull-request-{version}/buildWithParameters",
            auth=(jenkins_user, jenkins_token),
            data={"PULL_REQUEST_URL": pull_request_url},
        )
        self.log(f"Triggered jenkins job for PR {version}.")
