from .base import PullRequestSubscriber
from git.exc import GitCommandError
from mr.roboto.buildout import PloneCoreBuildout
from mr.roboto.events import MergedPullRequest
from mr.roboto.utils import get_pickled_data
from mr.roboto.utils import is_skip_commit_message
from mr.roboto.utils import plone_versions_targeted
from plone.releaser.manage import add_checkout
from pyramid.events import subscriber

import contextlib
import logging


logger = logging.getLogger()

# Changes in these repositories should not update buildout.coredev files
IGNORE_NO_AUTO_CHECKOUT = (
    "documentation",
    "icalendar",
)

# Authors that will not trigger a commit on buildout.coredev
# when their PRs get merged
IGNORE_PR_AUTHORS = (
    "pre-commit-ci[bot]",
    "dependabot[bot]",
)


@subscriber(MergedPullRequest)
class UpdateCoredevCheckouts(PullRequestSubscriber):
    def run(self):
        """Add package that got a pull request merged into checkouts.cfg

        - only for packages that are part of Plone coredev.
        - on all Plone coredev versions that track the branch that was
        targeted by the pull request
        """
        if not self.needs_update():
            return

        plone_versions = self.plone_versions()
        if not plone_versions:
            return

        self.call_plone_releaser(plone_versions)

    def needs_update(self):
        """Check if we really need to update buildout.coredev"""
        # pull requests on buildout.coredev itself do not need any extra work
        if self.repo_full_name == "plone/buildout.coredev":
            return False

        if self.repo_name in IGNORE_NO_AUTO_CHECKOUT:
            return False

        if self.pull_request_author in IGNORE_PR_AUTHORS:
            self.log(
                f"no commits on buildout.coredev as "
                f"user {self.pull_request_author} is ignored"
            )
            return False

        if self.is_skip_commit():
            self.log("Commit had a skip CI mark. No commit is done in buildout.coredev")
            return False

        return True

    def is_skip_commit(self):
        commit_message = self.g_merge_commit.commit.message
        return is_skip_commit_message(commit_message)

    def plone_versions(self):
        versions = plone_versions_targeted(
            self.repo_full_name, self.target_branch, self.event.request
        )
        if not versions:
            self.log(
                f"no plone coredev version tracks branch {self.target_branch} "
                f"of {self.repo_name}, checkouts.cfg not updated"
            )
            return []

        versions = self._already_in_all_checkouts(versions)
        return versions

    def _already_in_all_checkouts(self, plone_versions):
        """Which plone versions are missing the current repository in its checkouts?

        Given the list of plone versions the current repository is targeting,
        in which of those plone versions is the current repository not in checkouts.cfg?
        """
        checkouts = get_pickled_data(
            self.event.request.registry.settings["checkouts_file"]
        )
        plone_versions_missing = [
            version
            for version in plone_versions
            if self.repo_name not in checkouts[version]
        ]
        if not plone_versions_missing:
            self.log(
                f"is already on checkouts.cfg of all plone "
                f"versions that it targets {plone_versions}"
            )
        return plone_versions_missing

    def call_plone_releaser(self, versions):
        """Use plone.releaser `add-checkout`

        Add the current package to checkouts.cfg and much more,
        plone.releaser will take care of it.
        """
        for version in versions:
            attempts = 0
            while attempts < 5:
                try:
                    buildout = PloneCoreBuildout(version)
                except GitCommandError:
                    attempts += 1
                    if attempts == 5:
                        logger.error(
                            f"Could not checkout buildout.coredev on branch {version}"
                        )
                else:
                    with contextlib.chdir(buildout.location):
                        add_checkout(self.repo_name)
                        logger.info(
                            f"add to checkouts.cfg of buildout.coredev {version}"
                        )
                    buildout.cleanup()
                    break
