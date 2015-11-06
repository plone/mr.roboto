# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.buildout import PloneCoreBuildout
from mr.roboto.security import validatetoken

import json
import logging
import pickle


debug = False
logger = logging.getLogger('mr.roboto')


def add_log(request, who, message):
    logger.info(who + ' ' + message)


createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description='Creates github post-commit hooks.'
)


def getSourcesAndCheckouts(request):
    sources_dict = {}
    checkouts_dict = {}
    # We should remove all the actual hooks
    sources_file = request.registry.settings['sources_file']
    checkouts_file = request.registry.settings['checkouts_file']
    actual_plone_versions = request.registry.settings['plone_versions']

    # Clean Core Packages DB and sync to GH
    for plone_version in actual_plone_versions:
        msg = 'Checking sources and checkouts from plone {0}'
        add_log(
            request,
            'roboto',
            msg.format(plone_version)
        )

        # Add the core package to mongo
        buildout = PloneCoreBuildout(plone_version)
        sources = buildout.sources.keys()
        for source in sources:
            source_obj = buildout.sources[source]
            if source_obj.path is not None:
                key = (source_obj.path, source_obj.branch)
                if key not in sources_dict:
                    sources_dict[key] = [plone_version]
                else:
                    sources_dict[key].append(plone_version)

        checkouts_dict[plone_version] = []
        for checkout in buildout.checkouts.data:
            if checkout != '':
                checkouts_dict[plone_version].append(checkout)

    with open(sources_file, 'w') as sf:
        sf.write(pickle.dumps(sources_dict))

    with open(checkouts_file, 'w') as sf:
        sf.write(pickle.dumps(checkouts_dict))


@createGithubPostCommitHooks.get()
@validatetoken
def createGithubPostCommitHooksView(request):
    # sources_dict
    # {('package_path', 'branch'): ['5.0', '4.3']}
    #
    # checkouts_dict
    # {'5.0': ['package', '...']}
    debug = request.registry.settings['debug']
    # We should remove all the actual hooks
    github = request.registry.settings['github']
    roboto_url = request.registry.settings['roboto_url']

    getSourcesAndCheckouts(request)

    # hooks URL
    commit_url = roboto_url + 'run/corecommit'
    pull_url = roboto_url + 'run/pullrequest'

    messages = []
    # set hooks on github
    for repo in github.get_organization('plone').get_repos():

        hooks = repo.get_hooks()

        # Remove the old hooks
        for hook in hooks:

            # if hook.name == 'web' and (hook.config['url'].find(roboto_url)
            #  or hook.config['url'].find('jenkins.plone.org')):
            if hook.name == 'web' and \
                    hook.config['url'].find('roboto') and \
                    not hook.config['url'].find('github-webhook'):
                add_log(request, 'github', 'Removing hook ' + str(hook.config))
                if debug:
                    print 'Debug removing hook'
                else:
                    hook.delete()

        # Add the new hooks
        msg = 'Creating hook {0} and {1}'
        add_log(request, 'github', msg.format(commit_url, pull_url))
        messages.append('Creating hook ' + commit_url)
        try:
            if debug:
                print 'Debug creating hook'
            else:
                data = {
                    'url': commit_url,
                    'secret': request.registry.settings['api_key']
                }
                repo.create_hook('web', data, 'push', True)
                repo.create_hook('web', data, 'pull_request', True)
        except Exception:
            pass
    return json.dumps(messages)
