from pyramid.config import Configurator

from security import RequestWithAttributes

from plonejenkins.middleware.db import ReposDB, PullsDB

from plonejenkins.middleware.plonegithub import PloneGithub
from jenkins import Jenkins


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings,
                          request_factory=RequestWithAttributes)

    # adds cornice
    config.include("cornice")

    config.registry.settings['api_key'] = settings['api_key']

    config.registry.settings['jenkins'] = Jenkins(settings['jenkins_url'], settings['jenkins_username'], settings['jenkins_password'])

    config.registry.settings['github'] = PloneGithub(settings['github_user'], settings['github_password'])

    config.registry.settings['core'] = ReposDB(settings['core_repos_db'])
    config.registry.settings['pulls'] = PullsDB(settings['core_pulls_db'])

    config.registry.settings['log_file'] = settings['log_file']

    # adds cornice
    config.include("cornice")

    config.scan("plonejenkins.middleware.views")

    config.end()

    return config.make_wsgi_app()
