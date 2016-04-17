# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from mr.roboto.security import validate_github

import json
import logging


logger = logging.getLogger('mr.roboto')

pull_request_service = Service(
    name='Handle pull requests',
    path='/run/pull-request',
    description='Emit an event if the pull request is to a Plone core package'
)


@pull_request_service.post()
@validate_github
def handle_pull_request(request):
    """Handle pull request events.

    Verify that the pull request meets our criteria and notify about it,
    so subscribers can perform actions on it.
    """
    # bail out early if it's just a github check
    payload = json.loads(request.POST['payload'])
    if 'action' not in payload:
        return json.dumps({'message': 'No action, nothing can be done'})

    action = payload['action']
    pull_request = payload['pull_request']
    logger.info(
        u'Got pull request {0} with action {1}'.format(
            payload['pull_request']['html_url'],
            action,
        )
    )
    if action == 'opened':
        request.registry.notify(
            NewPullRequest(pull_request, request)
        )
    elif action == 'synchronize':
        request.registry.notify(
            UpdatedPullRequest(pull_request, request)
        )

    msg = 'Thanks! Handlers already took care of this pull request'
    return json.dumps({'message': msg, })
