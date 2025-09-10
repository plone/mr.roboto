from functools import cached_property
from mr.roboto.utils import shorten_pull_request_url
from requests.exceptions import RequestException

import logging
import requests


logger = logging.getLogger("mr.roboto")


IGNORE_USER_NO_AGREEMENT = (
    "dependabot[bot]",
    "pre-commit-ci[bot]",
    "web-flow",
    "weblate",
)

IGNORE_NO_TEST_NEEDED = (
    "icalendar",
    "plone.releaser",
    "plone.versioncheck",
)


# Ignore packages that have no influence on Jenkins.
IGNORE_NO_JENKINS = IGNORE_NO_TEST_NEEDED + (
    "documentation",
    "plone.recipe.zeoserver",
    "plone.recipe.zope2instance",
)


IGNORE_WEBLATE = {
    # Repo   Ignored individual user checks
    "volto": ["weblate"]
}


class PullRequestSubscriber:
    def __init__(self, event):
        self.event = event
        self.run()

    @cached_property
    def github(self):
        return self.event.request.registry.settings["github"]

    @cached_property
    def short_url(self):
        return shorten_pull_request_url(self.event.pull_request["html_url"])

    @cached_property
    def pull_request(self):
        return self.event.pull_request

    @cached_property
    def repo_name(self):
        return self.pull_request["base"]["repo"]["name"]

    @cached_property
    def pull_request_author(self):
        return self.pull_request["user"]["login"]

    @cached_property
    def repo_full_name(self):
        return self.pull_request["base"]["repo"]["full_name"]

    @cached_property
    def g_pull(self):
        """Get pygithub's pull request object and the last commit on it"""
        org = self.pull_request["base"]["repo"]["owner"]["login"]
        pull_number = int(self.pull_request["number"])

        g_org = self.github.get_organization(org)
        g_repo = g_org.get_repo(self.repo_name)
        return g_repo.get_pull(pull_number)

    @cached_property
    def g_issue(self):
        """Get pygithub's issue for the current pull request"""
        org = self.pull_request["base"]["repo"]["owner"]["login"]
        pull_number = int(self.pull_request["number"])

        g_org = self.github.get_organization(org)
        g_repo = g_org.get_repo(self.repo_name)
        return g_repo.get_issue(pull_number)

    @cached_property
    def g_repo(self):
        org = self.pull_request["base"]["repo"]["owner"]["login"]
        g_org = self.github.get_organization(org)
        return g_org.get_repo(self.repo_name)

    @cached_property
    def g_merge_commit(self):
        if self.g_pull.is_merged():
            merge_commit_sha = self.g_pull.merge_commit_sha
            merge_commit = self.g_repo.get_commit(merge_commit_sha)
            return merge_commit

    @cached_property
    def commits_url(self):
        return self.pull_request["commits_url"]

    @cached_property
    def target_branch(self):
        return self.pull_request["base"]["ref"]

    def run(self):
        raise NotImplementedError  # pragma: no cover

    def log(self, msg, level="info"):
        if level == "warn":  # pragma: no cover
            logger.warning(f"PR {self.short_url}: {msg}")
            return
        logger.info(f"PR {self.short_url}: {msg}")

    def get_pull_request_last_commit(self):
        return self.g_pull.get_commits().reversed[0]

    def get_json_commits(self):
        """From a commits_url like
        https://github.com/plone/mr.roboto/pull/34/commits
        return the JSON provided by github, or None if something happens
        """
        try:
            commits_data = requests.get(self.commits_url)
        except RequestException:
            self.log("error while trying to get its commits")
            return

        try:
            json_data = commits_data.json()
        except ValueError:
            self.log("error while getting its commits in JSON")
            return

        return json_data

    def is_weblate(self, commit_info):
        """check whether this commit info belongs to a user
        that we have to ignore.

        When checking weblate commits, we often found this kind of info

        {
            ...
            "author": null,
            "committer": {"login": "weblate", ...},
            ...
        },

        This is because weblate is in itself a git repository and this JSON
        is produced by GitHub.

        Sometimes some weblate addons have not a corresponding user on GitHub
        so the `author` value comes as `null`.

        In such cases our check (see `check_membership`) does not work, because
        we check for both `author` and `committer`.

        This is a shortcut, to check whether the committer login is something we
        previously know, and if so we ignore it.

        """
        if self.repo_name in IGNORE_WEBLATE:
            if (
                commit_info.get("committer", {}).get("login", "")
                in IGNORE_WEBLATE[self.repo_name]
            ):
                return True

        return False

    def check_membership(self, json_data):
        plone_org = self.github.get_organization("plone")
        unknown = []
        members = []
        not_foundation = []
        for commit_info in json_data:
            if not self.is_weblate(commit_info):
                for user in ("committer", "author"):
                    try:
                        login = commit_info[user]["login"]
                    except TypeError:
                        self.log(f"commit does not have {user} user info")
                        unknown.append(commit_info["commit"]["author"]["name"])
                        continue

                    if login in IGNORE_USER_NO_AGREEMENT:
                        continue

                    # avoid looking up users twice
                    if login in members or login in not_foundation:
                        continue

                    g_user = self.github.get_user(login)
                    if plone_org.has_in_members(g_user):
                        members.append(login)
                    else:
                        not_foundation.append(login)

        return not_foundation, unknown
