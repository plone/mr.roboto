from .base import PullRequestSubscriber
from datetime import datetime
from github import GithubException
from github import InputGitAuthor
from github import InputGitTreeElement
from mr.roboto.events import MergedPullRequest
from mr.roboto.utils import get_pickled_data
from mr.roboto.utils import is_skip_commit_message
from mr.roboto.utils import plone_versions_targeted
from pyramid.events import subscriber


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

        self.add_package_to_checkouts(plone_versions)

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

    def add_package_to_checkouts(self, versions):
        """Add package to checkouts.cfg on buildout.coredev plone version"""
        last_commit = self.get_pull_request_last_commit()
        user = InputGitAuthor(
            last_commit.commit.author.name,
            last_commit.commit.author.email,
            datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        org = self.github.get_organization("plone")
        repo = org.get_repo("buildout.coredev")

        for version in versions:
            attempts = 0
            while attempts < 5:
                try:
                    self.make_commit(repo, version, user)
                except GithubException:  # pragma: no cover
                    attempts += 1
                    if attempts == 5:
                        self.log(
                            f"Could not update checkouts.cfg of {version} "
                            f"with {self.repo_name}",
                            level="warn",
                        )
                else:
                    self.log(f"add to checkouts.cfg of buildout.coredev {version}")
                    break

    def make_commit(self, repo, version, user):
        filename = "checkouts.cfg"
        head_ref = repo.get_git_ref(f"heads/{version}")
        checkouts_cfg_file = repo.get_contents(filename, head_ref.object.sha)
        line = f"    {self.repo_name}\n"
        checkouts_content = checkouts_cfg_file.decoded_content.decode()
        checkouts_new_data = checkouts_content + line
        latest_commit = repo.get_git_commit(head_ref.object.sha)
        base_tree = latest_commit.tree
        mode = [t.mode for t in base_tree.tree if t.path == filename]
        if mode:  # pragma: no cover
            mode = mode[0]
        else:
            mode = "100644"

        element = InputGitTreeElement(
            path=filename,
            mode=mode,
            type=checkouts_cfg_file.type,
            content=checkouts_new_data,
        )
        new_tree = repo.create_git_tree([element], base_tree)

        new_commit = repo.create_git_commit(
            f"[fc] Add {self.repo_name} to {filename}",
            new_tree,
            [latest_commit],
            user,
            user,
        )
        head_ref.edit(sha=new_commit.sha, force=False)
