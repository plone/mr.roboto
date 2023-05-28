from collections import namedtuple
from cornice import Service
from github.GithubException import GithubException
from github.GithubException import UnknownObjectException
from mr.roboto.security import validate_service_token

import json
import logging


logger = logging.getLogger("mr.roboto")


createGithubPostCommitHooks = Service(
    name="Create github post-commit hooks",
    path="/run/githubcommithooks",
    description="Creates github post-commit hooks.",
)


@createGithubPostCommitHooks.get()
@validate_service_token
def create_github_post_commit_hooks_view(request):
    """Re-create hooks on github

    Removes all existing hooks on all repositories on github plone and
    collective organizations and creates them anew.
    """
    github = request.registry.settings["github"]
    roboto_url = request.registry.settings["roboto_url"]

    # hooks URL
    Hook = namedtuple("Hook", ["url", "events"])
    roboto_hooks = [
        Hook(f"{roboto_url}/run/corecommit", ["push"]),
        Hook(f"{roboto_url}/run/pull-request", ["pull_request"]),
        Hook(f"{roboto_url}/run/comment", ["issue_comment"]),
    ]

    messages = []

    one_repo = request.GET.get("repo", None)
    if one_repo:
        msg = f"Create hooks only for {one_repo}"
        logger.info(msg)
        try:
            repo = github.get_organization("plone").get_repo(one_repo)
        except UnknownObjectException:
            try:
                repo = github.get_organization("collective").get_repo(one_repo)
            except UnknownObjectException:
                return json.dumps({"message": f"Repository {one_repo} not found"})
        messages.append(update_hooks_on_repo(repo, roboto_hooks, request))
        return json.dumps(messages)

    collective_repos = [
        repo.strip()
        for repo in request.registry.settings["collective_repos"].split(",")
        if repo.strip()
    ]
    collective = github.get_organization("collective")
    for repo_name in collective_repos:
        repo = collective.get_repo(repo_name.strip())
        messages.append(update_hooks_on_repo(repo, roboto_hooks, request))

    for repo in github.get_organization("plone").get_repos():
        messages.append(update_hooks_on_repo(repo, roboto_hooks, request))

    return json.dumps(messages)


def update_hooks_on_repo(repo=None, new_hooks=None, request=None):
    debug = request.registry.settings["debug"]

    # Remove old hooks
    hooks = repo.get_hooks()
    for hook in hooks:
        if hook.name == "web":
            hook_url = hook.config["url"]
            if (
                hook_url.find("roboto/run/") != -1
                or hook_url.find("github-webhook") != -1
            ):
                logger.info(f"github Removing hook {hook.config}")
                if debug:
                    logger.info(f"Debug removing hook {repo.name}")
                else:
                    hook.delete()

    # Add new hooks
    msg = f"github Creating hooks on {repo.name}"
    logger.info(msg)
    try:
        if debug:
            logger.info("Debug creating hooks")
        else:
            for hook in new_hooks:
                config = {
                    "url": hook.url,
                    "secret": request.registry.settings["api_key"],
                }
                repo.create_hook("web", config, hook.events, True)
            if repo.name == "buildout.coredev":
                jenkins_url = request.registry.settings["jenkins_url"]
                config = {
                    "url": f"{jenkins_url}/github-webhook/",
                    "secret": request.registry.settings["api_key"],
                }
                repo.create_hook("web", config, ["*"], True)

    except GithubException:
        logger.exception(f"Error creating hook on {repo.name}")

    return msg
