import os, sys

from paste.deploy import loadapp

application = loadapp('config:/home/bitnami/mr.roboto/production.ini')

