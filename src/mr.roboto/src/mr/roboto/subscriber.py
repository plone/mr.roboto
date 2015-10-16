# -*- encoding: utf-8 -*-
from mr.roboto import templates
from mr.roboto.events import CommitAndMissingCheckout
from mr.roboto.events import NewCoreDevPush
from pyramid.events import subscriber
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

import logging
import requests


logger = logging.getLogger('mr.roboto')


def get_info_from_commit(commit):
    diff = requests.get(commit['url'] + '.diff').content

    files = ['A %s' % f for f in commit['added']]
    files.extend('M %s' % f for f in commit['modified'])
    files.extend('D %s' % f for f in commit['removed'])

    short_commit_msg = commit['message'].split('\n')[0][:60]
    reply_to = '%s <%s>' % (commit['committer']['name'], commit['committer']['email'])

    return {
        'diff': diff,
        'files': files,
        'short_commit_msg': short_commit_msg,
        'reply_to': reply_to,
        'sha': commit['id']
    }


def send_to_missing_checkout(mailer, who, repo, branch, pv, email):
    msg = Message(
        subject='CHECKOUT ERROR %s %s' % (repo, branch),
        sender="Jenkins Job FAIL <jenkins@plone.org>",
        recipients=["ramon.nb@gmail.com", "tisto@plone.org", email], # XXX also to testbot
        body=templates['error_commit_checkout.pt'](
            who=who,
            repo=repo,
            branch=branch,
            pv=pv),
        )
    mailer.send_immediately(msg, fail_silently=False)


def send_to_cvs(payload, mailer, result=""):
    # Send a mail
    if len(payload['commits']) < 40:
        # safeguard against github getting confused and sending us the entire history

        for commit in payload['commits']:

            commit_data = get_info_from_commit(commit)

            data = {
                'push': payload,
                'commit': commit,
                'files': '\n'.join(commit_data['files']),
                'diff': commit_data['diff'],
                'result': result
            }

            msg = Message(
                subject='%s/%s: %s' % (payload['repository']['name'],
                                       payload['ref'].split('/')[-1],
                                       commit_data['short_commit_msg']),
                sender="%s <svn-changes@plone.org>" % commit['committer']['name'],
                recipients=["plone-cvs@lists.sourceforge.net"],
                body=templates['commit_email.pt'](**data),
                extra_headers={'Reply-To': commit_data['reply_to']}
            )

            mailer.send_immediately(msg, fail_silently=False)


@subscriber(NewCoreDevPush)
def send_main_on_coredev(event):
    mailer = get_mailer(event.request)
    payload = event.payload
    logger.info("Sending mail because of push to coredev " + payload['repository']['name'])
    send_to_cvs(payload, mailer)


@subscriber(CommitAndMissingCheckout)
def send_main_on_missing_checkout(event):
    mailer = get_mailer(event.request)
    logger.info("Sending mail because of push to coredev without correct checkout " + event.repo + ' ' + event.who )
    send_to_missing_checkout(
        mailer,
        event.who,
        event.repo,
        event.branch,
        event.pv,
        event.email)
