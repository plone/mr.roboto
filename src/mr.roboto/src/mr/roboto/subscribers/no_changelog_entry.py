from .base import PullRequestSubscriber
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from pyramid.events import subscriber
from unidiff import PatchSet

import re
import requests


VALID_CHANGELOG_FILES = re.compile(
    r"(.pre-commit-config|CHANGES|HISTORY|CHANGELOG).(txt|rst|md|yaml)$"
)

IGNORE_NO_CHANGELOG = (
    ".github",
    "buildout.coredev",
    "dependabot[bot]",
    "documentation",
    "jenkins.plone.org",
    "mockup",
    "mr.roboto",
    "planet.plone.org",
    "plone-backend",
    "plone-frontend",
    "plone.jenkins_node",
    "plone.jenkins_server",
    "ploneorg.core",
    "ploneorg.theme",
    "pre-commit-ci[bot]",
    "training",
)


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnNoChangelogEntry(PullRequestSubscriber):
    def __init__(self, event):
        self.status_context = "Changelog verifier"

        super().__init__(event)

    def run(self):
        """If the pull request does not add a changelog entry, warn about it"""
        if self.repo_name in IGNORE_NO_CHANGELOG:
            self.log("no need to have a changelog entry")
            return

        status = "success"
        description = "Entry found"
        roboto_url = self.event.request.registry.settings["roboto_url"]

        # check if the pull request modifies the changelog file
        diff_url = self.pull_request["diff_url"]
        diff_data = requests.get(diff_url)
        # try:
        #    patch_data = PatchSet(
        #        diff_data.content.splitlines(), encoding=diff_data.encoding
        #    )
        # except UnicodeDecodeError:
        #    patch_data = []

        # https://github.com/plone/mr.roboto/issues/168
        patch_data = PatchSet(
            diff_data.content.splitlines(), encoding=diff_data.encoding
        )
        if len(patch_data) == 0:
            self.log("no files found on the patch")

        for diff_file in patch_data:
            if VALID_CHANGELOG_FILES.search(diff_file.path):
                break
            if "news/" in diff_file.path:
                # towncrier news snippet
                break
        else:
            status = "error"
            description = "No entry found!"

        # get the pull request and last commit
        last_commit = self.get_pull_request_last_commit()

        last_commit.create_status(
            status,
            target_url=f"{roboto_url}/missing-changelog",
            description=description,
            context=self.status_context,
        )

        self.log(f"changelog entry: {status}")
