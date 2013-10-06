# -*- encoding: utf-8 -*-
import requests

from pyramid_mailer.message import Message
from pyramid_mailer import get_mailer

from pyramid.events import subscriber

from mr.roboto.events import NewCoreDevBuildoutPush
from mr.roboto.events import KGSJobSuccess
from mr.roboto.events import KGSJobFailure

from mr.roboto import templates


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


def send_to_testbot(payload, mailer, result=""):

    repo = payload['repository']['name']

    if payload['pusher']['name'] == u'none':
        who = "NoBody <nobody@plone.org>"
    else:
        who = "%s <%s>" % (payload['pusher']['name'], payload['pusher']['email'])

    list_of_commits = ""
    for commit in payload['commits']:
        list_of_commits += commit['author']['name'] + '\n'
        list_of_commits += commit['message'] + '\n'
        list_of_commits += commit['url'] + '\n\n'

    data = {
        'repo': repo,
        'branch': payload['ref'].split('/')[-1],
        'name': who,
        'result': result,
        'commits': list_of_commits
    }

    msg = Message(
        subject='[FAIL] %s by %s' % (repo, who),
        sender="Jenkins Job FAIL <jenkins@plone.org>",
        # recipients=["plone-testbot@lists.plone.org"],
        recipients=["ramon.nb@gmail.com", "tisto@plone.org", "esteele@plone.org", "david.glick@plone.org"],
        body=templates['broken_job.pt'](**data),
        extra_headers={'Reply-To': who}
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
                #recipients=["ramon.nb@gmail.com", "contact@timostollenwerk.net", "david.glick@plone.org", "ericsteele47@gmail.com"],
                body=templates['commit_email.pt'](**data),
                extra_headers={'Reply-To': commit_data['reply_to']}
            )

            mailer.send_immediately(msg, fail_silently=False)


@subscriber(NewCoreDevBuildoutPush)
def send_mail_on_push(event):
    mailer = get_mailer(event.request)
    payload = event.payload
    send_to_cvs(payload, mailer)


@subscriber(KGSJobSuccess)
def kgs_job_success(event):
    # Send mail to plone-cvs with the results
    mailer = get_mailer(event.request)
    payload = event.payload
    result = event.result
    send_to_cvs(payload, mailer, result)


@subscriber(KGSJobFailure)
def kgs_job_failure(event):
    # Send mail to plone-cvs
    # with diff
    mailer = get_mailer(event.request)
    payload = event.payload
    result = event.result
    send_to_cvs(payload, mailer, result)

    # Send mail to test-bot
    # subject job FAIL package commit
    send_to_testbot(payload, mailer, result)


