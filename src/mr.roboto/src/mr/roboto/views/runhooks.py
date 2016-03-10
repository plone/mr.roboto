# -*- encoding: utf-8 -*-
from cornice import Service
from github.GithubException import GithubException
from mr.roboto.buildout import get_sources_and_checkouts
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
    # sources_dict
    # {('package_path', 'branch'): ['5.0', '4.3']}
    #
    # checkouts_dict
    # {'5.0': ['package', '...']}
    debug = request.registry.settings['debug']
    # We should remove all the actual hooks
    github = request.registry.settings['github']
    roboto_url = request.registry.settings['roboto_url']

    get_sources_and_checkouts(request)

    # hooks URL
    commit_url = roboto_url + 'run/corecommit'

    messages = []
    # set hooks on github
    for repo in github.get_organization('plone').get_repos():

        hooks = repo.get_hooks()

        # Remove the old hooks
        for hook in hooks:

            if hook.name == 'web' and \
                    hook.config['url'].find('roboto/run/') != -1:
                logger.info('github Removing hook ' + str(hook.config))
                if debug:
                    print 'Debug removing hook'
                else:
                    hook.delete()

        # Add the new hooks
        msg = 'github Creating hook {0} on {1}'
        logger.info(msg.format(commit_url, repo.name))
        messages.append('Creating hook ' + commit_url)
        try:
            if debug:
                print 'Debug creating hook'
            else:
                data = {
                    'url': commit_url,
                    'secret': request.registry.settings['api_key']
                }
                repo.create_hook('web', data, ['push', ], True)
        except GithubException, e:
            logging.exception('on repo {0}'.format(repo.name))
    return json.dumps(messages)
