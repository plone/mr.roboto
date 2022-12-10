from cornice import Service
from mr.roboto.events import MergedPullRequest
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from mr.roboto.security import validate_github
from mr.roboto.utils import shorten_pull_request_url

import json
import logging


logger = logging.getLogger('mr.roboto')

pull_request_service = Service(
    name='Handle pull requests',
    path='/run/pull-request',
    description='Emit an event if the pull request is to a Plone core package',
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
        return {'message': 'No action, nothing can be done'}
    short_url = shorten_pull_request_url(payload['pull_request']['html_url'])

    action = payload['action']
    pull_request = payload['pull_request']
    logger.info(f'PR {short_url}: with action {action}')
    if action in ('opened', 'reopened'):
        request.registry.notify(NewPullRequest(pull_request, request))
    elif action == 'synchronize':
        request.registry.notify(UpdatedPullRequest(pull_request, request))
    elif action == 'closed' and pull_request['merged']:
        request.registry.notify(MergedPullRequest(pull_request, request))
    else:
        msg = f'PR {short_url}: action "{action}" (merged: {pull_request["merged"]}) not handled'
        logger.info(msg)
        return {'message': msg}

    return {'message': 'Thanks! Handlers already took care of this pull request'}
