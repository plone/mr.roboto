# -*- encoding: utf-8 -*-
from collections import namedtuple
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

    Removes all existing hooks on all repositories on github plone and
    collective organizations and creates them anew.
    """
    github = request.registry.settings['github']
    roboto_url = request.registry.settings['roboto_url']

    # hooks URL
    Hook = namedtuple('Hook', ['url', 'events', ])
    roboto_hooks = [
        Hook(
            '{0}/run/corecommit'.format(roboto_url),
            ['push', ]
        ),
        Hook(
            '{0}/run/pull-request'.format(roboto_url),
            ['pull_request', ]
        ),
    ]

    messages = []

    collective_repos = [
        repo.strip()
        for repo in request.registry.settings['collective_repos'].split(',')
        if repo.strip()
    ]
    collective = github.get_organization('collective')
    for repo_name in collective_repos:
        repo = collective.get_repo(repo_name.strip())
        messages.append(
            update_hooks_on_repo(repo, roboto_hooks, request)
        )

    for repo in github.get_organization('plone').get_repos():
        messages.append(
            update_hooks_on_repo(repo, roboto_hooks, request)
        )

    return json.dumps(messages)


def update_hooks_on_repo(repo=None, new_hooks=None, request=None):
    debug = request.registry.settings['debug']

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
    msg = 'github Creating hooks on {0}'.format(repo.name)
    logger.info(msg)
    try:
        if debug:
            logger.info('Debug creating hooks')
        else:
            for hook in new_hooks:
                config = {
                    'url': hook.url,
                    'secret': request.registry.settings['api_key']
                }
                repo.create_hook('web', config, hook.events, True)
    except GithubException:
        logger.exception('Error creating hook on {0}'.format(repo.name))

    return msg
