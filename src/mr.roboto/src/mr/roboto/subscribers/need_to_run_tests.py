from .base import IGNORE_NO_JENKINS
from .base import IGNORE_NO_TEST_NEEDED
from .base import PullRequestSubscriber
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from mr.roboto.utils import plone_versions_targeted
from pyramid.events import subscriber


@subscriber(NewPullRequest, UpdatedPullRequest)
class WarnTestsNeedToRun(PullRequestSubscriber):
    def __init__(self, event):
        self.jenkins_pr_job_url = (
            "http://jenkins.plone.org/job/pull-request-{0}/build?delay=0sec"
        )
        self.status_context = "Plone Jenkins CI - pull-request-{0}"

        super().__init__(event)

    def run(self):
        """Create waiting status for all pull request jobs that should be run
        before a pull request can be safely merged
        """
        if self.repo_name in IGNORE_NO_JENKINS:
            self.log(f"Not adding pending Jenkins checks: {self.repo_name} ignored.")
            return

        plone_versions = self._plone_versions_targeted()
        python_versions = self.event.request.registry.settings["py_versions"]

        # get the pull request last commit
        last_commit = self.get_pull_request_last_commit()

        for plone_version in plone_versions:
            for py_version in python_versions[plone_version]:
                self._create_commit_status(last_commit, plone_version, py_version)
                self.log(
                    f"created pending status for plone {plone_version} on python {py_version}"
                )

    def _plone_versions_targeted(self):
        if self.repo_name in IGNORE_NO_TEST_NEEDED:
            self.log("skip adding test warnings, repo ignored")
            return []

        target_branch = self.pull_request["base"]["ref"]

        plone_versions = plone_versions_targeted(
            self.repo_full_name, target_branch, self.event.request
        )

        tracked_versions = self.event.request.registry.settings["plone_versions"]
        if (
            self.repo_full_name == "plone/buildout.coredev"
            and target_branch in tracked_versions
        ):
            plone_versions = (target_branch,)

        elif not plone_versions:
            self.log("does not target any Plone version")
            return []

        return plone_versions

    def _create_commit_status(self, commit, plone_version, python_version):
        combination = f"{plone_version}-{python_version}"
        commit.create_status(
            "pending",
            target_url=f"https://jenkins.plone.org/job/pull-request-{combination}/build?delay=0sec",
            description="Please run the job, click here --->",
            context=f"Plone Jenkins CI - pull-request-{combination}",
        )
