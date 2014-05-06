from pyramid.view import view_config

from mr.roboto.security import validatetoken
from mr.roboto.db import CorePackages, PLIPPackages, PLIPPackage
from mr.roboto.db import Push
from mr.roboto.db import Pushes
from mr.roboto.views.runcorejob import PYTHON_VERSIONS, OLD_PYTHON_VERSIONS, PLONE_VERSIONS_WITH_26

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


@view_config(route_name='view_info', renderer='mr.roboto:templates/push_info.pt')
def view_commit_info(context, request):
    if 'push' in request.GET:
        push_id = request.GET['push']
        pushes = Pushes(request.registry.settings['dm'])
        if push_id in pushes:
            push = pushes[push_id]
        jobs = [f for f in request.registry.settings['db']['jenkins_job'].find({'push': push.internal_identifier})]
        return dict(push=push, jobs=jobs)


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
            robot_tests = True if 'robot_test' in request.POST else False
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
                contact=contact,
                robot_tests=robot_tests)
            transaction.commit()
        if request.POST['action'] == 'delete':
            request.registry.settings['db']['plip'].remove({'description': request.POST['description']})

    plips = []
    for plip in list(request.registry.settings['db']['plip'].find()):
        if 'robot_tests' not in plip:
            plip['robot_tests'] = None
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


@view_config(route_name='pushs', renderer='mr.roboto:templates/pushs.pt')
def pushsPage(context, request):
    pushs = []
    for push in list(request.registry.settings['db']['push'].find().sort('date', 1).limit(100)):
        jobs_dict = []
        for job in list(request.registry.settings['db']['jenkins_job'].find({'push': push['internal_identifier']})):
            jobs_dict.append(job)
        push['jobs'] = jobs_dict
        pushs.append(push)
    return dict(pushs=pushs)

@view_config(route_name='coredevjobs', renderer='mr.roboto:templates/coredevjobs.pt')
def coredevjobsPage(context, request):
    plone_versions = request.registry.settings['plone_versions']
    result = []
    for plone_version in plone_versions:
        if plone_version in PLONE_VERSIONS_WITH_26:
            pyversions = OLD_PYTHON_VERSIONS
        else:
            pyversions = PYTHON_VERSIONS

        for pyversion in pyversions:
            data = {}
            data['python'] = pyversion
            data['plone'] = plone_version
            data['job'] = 'plone-' + plone_version + '-python-' + pyversion
            data['jobs'] = []
            for job in list(request.registry.settings['db']['jenkins_job'].find({'jk_name': data['job']}).sort('date', -1).limit(100)):
                pushs = list(request.registry.settings['db']['push'].find({'internal_identifier': job['push']}))
                job['push_info'] = pushs
                data['jobs'].append(job)
            result.append(data)
    return dict(jobs=result)
