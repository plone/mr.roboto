from pyramid.view import view_config
from mr.roboto import dir_for_kgs


@view_config(route_name='kgs', renderer='mr.roboto:templates/kgs.pt')
def kgs_for_version(context, request):
    """
    to get the buildout configuration for testing the package with a kgs you need to call it with :
    http://jenkins.plone.org/roboto/kgs?plone=4.3&python=2.7&package=plone.app.contenttypes
    """
    if 'plone' in request.GET and 'python' in request.GET and 'package' in request.GET:
        plone_version = request.GET['plone']
        python_version = request.GET['python']
        kgs_file = "%s/plone-%s-python-%s/snapshoot.cfg" % (dir_for_kgs, plone_version, python_version)
        directory_of_package = "src/%s" % (request.GET['package'])
        f = open(kgs_file, 'r')
        sources = f.read()
        f.close()
        return dict(directory_of_package=directory_of_package, sources=sources)

