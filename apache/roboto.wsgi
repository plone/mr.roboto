import os, sys
#from paste.deploy importo loadapp

#import site
#site.addsitedir('/home/bitnami/mr.roboto/eggs/site-packages')

from pyramid.paster import get_app, setup_logging
ini_path = '/home/bitnami/mr.roboto/production.ini'
setup_logging(ini_path)
application = get_app(ini_path, 'main')
#application = loadapp('config:/home/bitnami/mr.roboto/production.ini')

