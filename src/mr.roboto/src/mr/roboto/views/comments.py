# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.events import CommentOnPullRequest
from mr.roboto.security import validate_github
from mr.roboto.utils import shorten_comment_url
from mr.roboto.utils import shorten_pull_request_url

import json
import logging


logger = logging.getLogger('mr.roboto')


handle_comments = Service(
    name='Handle comments',
    path='/run/comment',
    description='Emit an event if comment is made on a pull request',
)


@handle_comments.post()
@validate_github
def handle_comment(request):
    """Handle comments on issues/pull requests events.

    Do some verification and issue internal events that will do they own thing.
    """
    # bail out early if it's just a github check ?? see pull requests
    payload = json.loads(request.POST['payload'])
    if 'action' not in payload:
        return 'No action'  # handle github pings

    if 'comment' not in payload:
        return 'Comment is missing in payload. No action.'

    if 'issue' not in payload or 'pull_request' not in payload['issue']:
        return 'The comment is not from a pull request. No action.'

    action = payload['action']
    comment_payload = payload['comment']
    comment_short_url = shorten_comment_url(comment_payload['html_url'])
    comment_user_id = comment_payload['user']['login']

    jenkins_user_id = request.registry.settings['jenkins_user_id']
    if comment_user_id == jenkins_user_id:

        logger.info(
            f'COMMENT {comment_short_url}: IGNORED as it is from {jenkins_user_id}'
        )
        return f'Comment on PR {comment_short_url} ignored as is from {jenkins_user_id}. No action.'

    pull_request_payload = payload['issue']['pull_request']
    pull_request_short_url = shorten_pull_request_url(pull_request_payload['html_url'])
    logger.info(
        u'COMMENT {0}: with action {1} on pull request {2}'.format(
            comment_short_url, action, pull_request_short_url
        )
    )
    if action == 'created':
        request.registry.notify(
            CommentOnPullRequest(comment_payload, pull_request_payload, request)
        )

    msg = 'Thanks! Handlers already took care of this comment'
    return json.dumps({'message': msg})
