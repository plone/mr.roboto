from pyramid.view import view_config

from mr.roboto.security import validatetoken
from mr.roboto.db import CorePackages, PLIPPackages, PLIPPackage
from mr.roboto.db import Push
from mr.roboto.db import Pushes


@view_config(route_name='dashboard', renderer='mr.roboto:templates/dashboard.pt')
def dashboard(context, request):
    job = request.registry.settings['db']['jenkins_job'].find({'jk_name': 'plone-5.0-python-2.7'}).sort('date', -1).next()


    push_id = job['push']

    pushes = Pushes(request.registry.settings['dm'])
    if push_id in pushes:
        push = pushes[push_id]
    jobs = [f for f in request.registry.settings['db']['jenkins_job'].find({'push': push.internal_identifier})]
    broken = False
    for job in jobs:
        if job['result'] is False:
            broken = True
            since = push['date']
    return dict(push=push, jobs=jobs, broken=broken, since=since)
