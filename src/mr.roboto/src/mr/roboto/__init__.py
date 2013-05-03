from pyramid.config import Configurator

from security import RequestWithAttributes

from mr.roboto.db import PullsDB

from mr.roboto.plonegithub import PloneGithub
from jenkins import Jenkins
import pymongo
import ast

from mongopersist import datamanager


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings,
                          request_factory=RequestWithAttributes)

    # adds cornice
    config.include("cornice")

    # adds pyramid_mailer
    config.include('pyramid_mailer')

    # plone versions
    config.registry.settings['plone_versions'] = ast.literal_eval(settings['plone_versions'])

    # roboto public url
    config.registry.settings['roboto_url'] = settings['roboto_url']

    # callback url (localhost for security)
    config.registry.settings['callback_url'] = settings['callback_url'] + '/callback/'

    # api_key to callback from gh
    config.registry.settings['api_key'] = settings['api_key']

    # jenkins object
    config.registry.settings['jenkins'] = Jenkins(settings['jenkins_url'], settings['jenkins_username'], settings['jenkins_password'])

    # github object
    config.registry.settings['github'] = PloneGithub(settings['github_user'], settings['github_password'])

    # db object
    config.registry.settings['conn'] = pymongo.Connection('localhost', 27017, tz_aware=False, fsync=False, j=False)
    config.registry.settings['db'] = config.registry.settings['conn'][settings['db_name']]
    dm = datamanager.MongoDataManager(
        config.registry.settings['conn'],
        default_database=settings['db_name'],
        root_database=settings['db_name'])
    config.registry.settings['dm'] = dm

    config.registry.settings['pulls'] = PullsDB(settings['core_pulls_db'])

    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('home', '/')
    # config.add_route('log', '/log')
    config.add_route('repos', '/repos')
    config.add_route('jobs', '/jobs')
    config.add_route('plips', '/plips')
    # config.add_route('status', '/status')

    # Automatic views
    config.scan("mr.roboto.views")
    config.scan("mr.roboto.subscriber")

    config.end()

    return config.make_wsgi_app()
