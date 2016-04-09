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

    files = ['A {0}'.format(f) for f in commit['added']]
    files.extend('M {0}'.format(f) for f in commit['modified'])
    files.extend('D {0}'.format(f) for f in commit['removed'])

    short_commit_msg = commit['message'].split('\n')[0][:60]
    reply_to = '{0} <{1}>'.format(
        commit['committer']['name'],
        commit['committer']['email']
    )

    return {
        'diff': diff,
        'files': files,
        'short_commit_msg': short_commit_msg,
        'full_commit_msg': commit['message'],
        'reply_to': reply_to,
        'sha': commit['id']
    }


def mail_missing_checkout(mailer, who, repo, branch, pv, email):
    msg = Message(
        subject='CHECKOUT ERROR {0} {1}'.format(repo, branch),
        sender='Jenkins Job FAIL <jenkins@plone.org>',
        recipients=[  # XXX also to testbot
            'ramon.nb@gmail.com',
            'tisto@plone.org',
            email,
        ],
        body=templates['error_commit_checkout.pt'](
            who=who,
            repo=repo,
            branch=branch,
            pv=pv),
        )
    mailer.send_immediately(msg, fail_silently=False)


def mail_to_cvs(payload, mailer):
    # safeguard against github getting confused and sending us the entire
    # history
    if len(payload['commits']) > 40:
        return

    for commit in payload['commits']:

        commit_data = get_info_from_commit(commit)

        data = {
            'push': payload,
            'commit': commit,
            'files': '\n'.join(commit_data['files']),
            'diff': commit_data['diff'],
        }

        msg = Message(
            subject='{0}/{1}: {2}'.format(
                payload['repository']['name'],
                payload['ref'].split('/')[-1],
                commit_data['short_commit_msg']),
            sender='{0} <svn-changes@plone.org>'.format(
                commit['committer']['name']
            ),
            recipients=['plone-cvs@lists.sourceforge.net'],
            body=templates['commit_email.pt'](**data),
            extra_headers={'Reply-To': commit_data['reply_to']}
        )

        mailer.send_immediately(msg, fail_silently=False)


@subscriber(NewCoreDevPush)
def send_main_on_coredev(event):
    mailer = get_mailer(event.request)
    payload = event.payload
    msg = 'Sending mail because of push to coredev {0}'
    logger.info(msg.format(payload['repository']['name']))
    mail_to_cvs(payload, mailer)


@subscriber(CommitAndMissingCheckout)
def send_main_on_missing_checkout(event):
    mailer = get_mailer(event.request)
    msg = 'Sending mail because of push to coredev and no checkout {0} {1}'
    logger.info(msg.format(event.repo, event.who))
    mail_missing_checkout(
        mailer,
        event.who,
        event.repo,
        event.branch,
        event.pv,
        event.email)
