# -*- encoding: utf-8 -*-
from cornice import Service
from github.GithubException import GithubException
from mr.roboto.buildout import PloneCoreBuildout
from mr.roboto.security import validate_token

import json
import logging
import pickle


logger = logging.getLogger('mr.roboto')


createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description='Creates github post-commit hooks.'
)


def get_sources_and_checkouts(request):
    """Get sources.cfg and checkouts.cfg from buildout.coredev

    Get them for all major plone releases
    (see plone_versions on mr.roboto's configuration),
    process and store their data on pickle files for later usage.
    """
    sources_dict = {}
    checkouts_dict = {}

    actual_plone_versions = request.registry.settings['plone_versions']

    for plone_version in actual_plone_versions:
        msg = 'Checking sources and checkouts from plone {0}'
        logger.info(msg.format(plone_version))
        buildout = PloneCoreBuildout(plone_version)

        for source in buildout.sources:
            source_obj = buildout.sources[source]
            if source_obj.path is not None:
                key = (source_obj.path, source_obj.branch)
                if key not in sources_dict:
                    sources_dict[key] = [plone_version]
                else:
                    sources_dict[key].append(plone_version)

        checkouts_dict[plone_version] = []
        for checkout in buildout.checkouts.data:
            if checkout:
                checkouts_dict[plone_version].append(checkout)

    sources_file = request.registry.settings['sources_file']
    with open(sources_file, 'w') as sf:
        sf.write(pickle.dumps(sources_dict))

    checkouts_file = request.registry.settings['checkouts_file']
    with open(checkouts_file, 'w') as sf:
        sf.write(pickle.dumps(checkouts_dict))


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
