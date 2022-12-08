from chameleon import PageTemplateLoader
from github import Github
from mr.roboto.security import RequestWithAttributes
from pyramid.config import Configurator

import ast
import logging
import os


# change requests logging so that it does not log so much
requests_logger = logging.getLogger('requests.packages.urllib3.connectionpool')
requests_logger.setLevel(logging.ERROR)

templates = PageTemplateLoader(os.path.join(os.path.dirname(__file__), 'templates'))


def main(global_config, **settings):
    """This function returns a Pyramid WSGI application"""
    config = Configurator(settings=settings, request_factory=RequestWithAttributes)

    # add webservice support
    config.include('cornice')

    # adds mailer and chameleon templates
    config.include('pyramid_mailer')
    config.include('pyramid_chameleon')

    # plone versions
    config.registry.settings['plone_versions'] = ast.literal_eval(
        settings['plone_versions']
    )

    # dictionary the list of python versions (value) per plone version (key)
    config.registry.settings['py_versions'] = ast.literal_eval(
        settings['py_versions']
    )

    # github users
    config.registry.settings['github_users'] = ast.literal_eval(
        settings['github_users']
    )

    # roboto public url
    config.registry.settings['roboto_url'] = settings['roboto_url']

    # api_key to callback from gh
    config.registry.settings['api_key'] = settings['api_key']

    # Debug
    config.registry.settings['debug'] = False
    if 'debug' in settings:
        config.registry.settings['debug'] = settings['debug'] == 'True'

    config.registry.settings['sources_file'] = settings['sources_file']
    config.registry.settings['checkouts_file'] = settings['checkouts_file']

    # github object
    config.registry.settings['github'] = Github(settings['github_token'])

    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('home', '/')
    config.add_route('log', '/log')
    config.add_route('sources', '/sources.json')
    config.add_route('checkouts', '/checkouts.json')
    config.add_route('update_pickles', '/update-sources-and-checkouts')
    config.add_route('missing_changelog', '/missing-changelog')
    config.add_route('branches', '/branches')

    # Automatic views
    config.scan('mr.roboto.views')
    config.scan('mr.roboto.subscriber')

    config.end()

    return config.make_wsgi_app()
