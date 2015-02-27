from pyramid.config import Configurator

from security import RequestWithAttributes


from github import Github
import ast

from chameleon import PageTemplateLoader
import os

templates = PageTemplateLoader(os.path.join(os.path.dirname(__file__), "templates"))


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings,
                          request_factory=RequestWithAttributes)

    # adds cornice
    config.include("cornice")

    # adds pyramid_mailer
    config.include('pyramid_mailer')
    config.include('pyramid_chameleon')

    # plone versions
    config.registry.settings['plone_versions'] = ast.literal_eval(settings['plone_versions'])

    # roboto public url
    config.registry.settings['roboto_url'] = settings['roboto_url']

    # api_key to callback from gh
    config.registry.settings['api_key'] = settings['api_key']

    # Debug
    if 'debug' in settings:
        config.registry.settings['debug'] = (settings['debug'] == 'True')
    else:
        config.registry.settings['debug'] = False

    config.registry.settings['sources_file'] = settings['sources_file']
    config.registry.settings['checkouts_file'] = settings['checkouts_file']

    # github object
    config.registry.settings['github'] = Github(settings['github_user'], settings['github_password'])

    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('home', '/')
    config.add_route('log', '/log')
    # config.add_route('sources', '/sources.json')
    # config.add_route('checkouts', '/checkouts.json')

    # Automatic views
    config.scan("mr.roboto.views")
    config.scan("mr.roboto.subscriber")

    config.end()

    return config.make_wsgi_app()
