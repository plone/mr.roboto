from pyramid.view import view_config

from mr.roboto.security import validatetoken
from mr.roboto.db import CorePackages, PLIPPackages, PLIPPackage

import logging
import transaction

log = logging.getLogger('HOME')


@view_config(route_name='home', renderer='mr.roboto:templates/home.pt')
def homePage(context, request):
    info = {}
    return dict(info=info)


@validatetoken
@view_config(route_name='log', renderer='mr.roboto:templates/log.pt')
def logPage(context, request):
    f = open('roboto.log', 'r')
    log = f.read()
    f.close()
    return dict(log=log)


@view_config(route_name='plips', renderer='mr.roboto:templates/plip.pt')
def plipPage(context, request):
    if 'action' in request.POST and request.POST['key'] == request.registry.settings['api_key']:
        if request.POST['action'] == 'add':
            repos_to_check = []
            repos = request.POST['repo']
            for line in repos.split('\r\n'):
                if len(line.split(' ')) > 1:
                    (repo, branch) = line.split(' ')
                    repos_to_check.append([repo, branch])
            buildout = request.POST['buildout']
            description = request.POST['description']
            if 'url' in request.POST:
                url = request.POST['url']
            else:
                url = ''
            buildout_branch = request.POST['buildout_branch']
            buildout_file = request.POST['buildout_file']
            contact = request.POST['contact'] if 'contact' in request.POST else ''
            if request.registry.settings['db']['plip'].find({'description': description}).count() > 0:
                request.registry.settings['db']['plip'].remove({'description': description})
            dm = request.registry.settings['dm']
            PLIPPackages(dm)[description] = PLIPPackage(
                repo=repos_to_check,
                buildout=buildout,
                description=description,
                url=url,
                buildout_branch=buildout_branch,
                buildout_file=buildout_file,
                contact=contact)
            transaction.commit()
        if request.POST['action'] == 'delete':
            request.registry.settings['db']['plip'].remove({'description': request.POST['description']})

    plips = []
    for plip in list(request.registry.settings['db']['plip'].find()):
        plips.append(plip)

    return dict(plips=plips)


@view_config(route_name='repos', renderer='mr.roboto:templates/core.pt')
def reposPage(context, request):
    plone_versions = request.registry.settings['plone_versions']
    packages = {}
    for plone_version in plone_versions:
        version_packages = []
        for package in list(request.registry.settings['db']['core_package'].find({'plone_version': plone_version})):
            version_packages.append(package)
        packages[plone_version] = version_packages
    return dict(packages=packages)


@view_config(route_name='jobs', renderer='mr.roboto:templates/jobs.pt')
def jobsPage(context, request):
    jobs = []
    for job in list(request.registry.settings['db']['jenkins_job'].find().sort('date', -1).limit(100)):
        jobs.append(job)
    return dict(jobs=jobs)
