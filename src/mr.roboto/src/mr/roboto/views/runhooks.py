# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatetoken
from mr.roboto.buildout import PloneCoreBuildout

import logging
import pickle
import json

debug = False
logger = logging.getLogger('mr.roboto')


def add_log(request, who, message):
    logger.info(who + " " + message)

createGithubPostCommitHooks = Service(
    name='Create github post-commit hooks',
    path='/run/githubcommithooks',
    description="Creates github post-commit hooks."
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
        add_log(request, 'roboto', 'Checking sources and checkouts from plone %s' % plone_version)

        # Add the core package to mongo
        buildout = PloneCoreBuildout(plone_version)
        sources = buildout.sources.keys()
        for source in sources:
            source_obj = buildout.sources[source]
            if source_obj.path is not None:
                if (source_obj.path, source_obj.branch) not in sources_dict:
                    sources_dict[(source_obj.path, source_obj.branch)] = [plone_version]
                else:
                    sources_dict[(source_obj.path, source_obj.branch)].append(plone_version)

        checkouts_dict[plone_version] = []
        for checkout in buildout.checkouts.data:
            if checkout != '':
                checkouts_dict[plone_version].append(checkout)

    sf = open(sources_file, 'w')
    sf.write(pickle.dumps(sources_dict))
    sf.close()

    sf = open(checkouts_file, 'w')
    sf.write(pickle.dumps(checkouts_dict))
    sf.close()


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

            #if hook.name == 'web' and (hook.config['url'].find(roboto_url) or hook.config['url'].find('jenkins.plone.org')):
            if hook.name == 'web' and (hook.config['url'].find(roboto_url) or hook.config['url'].find('roboto')):
                add_log(request, 'github', 'Removing hook ' + str(hook.config))
                if debug:
                    print "Debug removing hook"
                else:
                    hook.delete()

        # Add the new hooks
        add_log(request, 'github', 'Creating hook ' + commit_url + ' and ' + pull_url)
        messages.append('Creating hook ' + commit_url)
        try:
            if debug:
                print "Debug creating hook"
            else:
                repo.create_hook('web', {'url': commit_url, 'secret': request.registry.settings['api_key']}, 'push', True)
                repo.create_hook('web', {'url': pull_url, 'secret': request.registry.settings['api_key']}, 'pull_request', True)
        except:
            pass
    return json.dumps(messages)
