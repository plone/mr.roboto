from pyramid.view import view_config

from mr.roboto.security import validatetoken
from mr.roboto.db import CorePackages, PLIPPackages, PLIPPackage
from mr.roboto.db import Push
from mr.roboto.db import Pushes


@view_config(route_name='dashboard', renderer='mr.roboto:templates/dashboard.pt')
def dashboard(context, request):
    jobs5 = list(request.registry.settings['db']['jenkins_job'].find({'jk_name': 'plone-5.0-python-2.7'}).sort({'date', -1}))

    # Run the core jobs related with this commit on jenkins
    job = jobs5[0]

    push_id = job['push']

    pushes = Pushes(request.registry.settings['dm'])
    if push_id in pushes:
        push = pushes[push_id]
    jobs = [f for f in request.registry.settings['db']['jenkins_job'].find({'push': push.internal_identifier})]
    return dict(push=push, jobs=jobs)
