# -*- encoding: utf-8 -*-
from cornice import Service
from github.GithubException import GithubException
from mr.roboto.security import validate_service_token

import json
import logging


logger = logging.getLogger('mr.roboto')


createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description='Creates github post-commit hooks.'
)


@createGithubPostCommitHooks.get()
@validate_service_token
def create_github_post_commit_hooks_view(request):
    """Re-create hooks on github

    Removes all existing hooks on all repositories on github plone organization
    and creates them anew.
    """
    github = request.registry.settings['github']
    collective_repos = request.registry.settings['collective_repos']

    messages = []
    for repo in github.get_organization('plone').get_repos():
        messages.append(
            update_hooks_on_repo(repo, request)
        )

    collective_repos = [
        repo.strip()
        for repo in collective_repos.split(',')
        if repo.strip()
    ]
    collective = github.get_organization('collective')
    for repo_name in collective_repos:
        repo = collective.get_repo(repo_name.strip())
        messages.append(
            update_hooks_on_repo(repo, request)
        )

    return json.dumps(messages)


def update_hooks_on_repo(repo=None, request=None):
    debug = request.registry.settings['debug']
    # hooks URL
    roboto_url = request.registry.settings['roboto_url']
    commit_url = '{0}/run/corecommit'.format(roboto_url)

    # Remove old hooks
    hooks = repo.get_hooks()
    for hook in hooks:
        if hook.name == 'web' and \
                hook.config['url'].find('roboto/run/') != -1:
            logger.info(
                'github Removing hook {0}'.format(str(hook.config))
            )
            if debug:
                logger.info('Debug removing hook {0}'.format(repo.name))
            else:
                hook.delete()

    # Add new hooks
    msg = 'github Creating hook {0} on {1}'.format(commit_url, repo.name)
    logger.info(msg)
    try:
        if debug:
            logger.info('Debug creating hook')
        else:
            config = {
                'url': commit_url,
                'secret': request.registry.settings['api_key']
            }
            repo.create_hook('web', config, ['push', ], True)
    except GithubException:
        logger.exception('Error creating hook on {0}'.format(repo.name))

    return msg
