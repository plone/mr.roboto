# -*- encoding: utf-8 -*-
from cornice import Service
from github.GithubException import GithubException
from mr.roboto.security import validate_token

import json
import logging


logger = logging.getLogger('mr.roboto')


createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description='Creates github post-commit hooks.'
)


@createGithubPostCommitHooks.get()
@validate_token
def create_github_post_commit_hooks_view(request):
    """Re-create hooks on github

    Removes all existing hooks on all repositories on github plone organization
    and creates them anew.
    """
    debug = request.registry.settings['debug']
    github = request.registry.settings['github']
    roboto_url = request.registry.settings['roboto_url']

    # hooks URL
    commit_url = '{0}/run/corecommit'.format(roboto_url)

    messages = []
    for repo in github.get_organization('plone').get_repos():

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
        msg = 'github Creating hook {0} on {1}'
        logger.info(msg.format(commit_url, repo.name))
        messages.append('Creating hook {0}'.format(commit_url))
        try:
            if debug:
                print 'Debug creating hook'
            else:
                config = {
                    'url': commit_url,
                    'secret': request.registry.settings['api_key']
                }
                repo.create_hook('web', config, ['push', ], True)
        except GithubException:
            logging.exception('Error creating hook on {0}'.format(repo.name))

    return json.dumps(messages)
