import os, sys
#sys.path.append('/var/plone/tempus.buildout')
#os.environ['PYTHON_EGG_CACHE'] = '/var/plone/tempus.buildout/eggs:/var/plone/tempus.buildout/develop-eggs'

from paste.deploy import loadapp

application = loadapp('config:/var/plone/tempus.buildout/development.ini')
