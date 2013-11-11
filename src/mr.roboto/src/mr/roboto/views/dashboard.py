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
    jobs = (job,)    
    broken = False
    since = ""
    by = ""
    for job in jobs:
        if 'result' in job and (job['result'] is False or job['result'] is None):
            broken = True
            since = job['date']
            push_obj = pushes[job['push']]
            by = push_obj.who
            broken_jobs = request.registry.settings['db']['jenkins_job'].find({'jk_name': 'plone-5.0-python-2.7'}).sort('date', -1)
            for broken_job in broken_jobs:
                if broken_job['result'] is False or broken_job['result'] is None:
                    since = broken_job['date']
                    push_obj = pushes[broken_job['push']]
                    by = push_obj.who
                else:
                    break
    return dict(push=push, jobs=jobs, broken=broken, since=since, by=by)
