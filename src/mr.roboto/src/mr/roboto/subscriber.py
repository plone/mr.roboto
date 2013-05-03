# -*- encoding: utf-8 -*-
import requests
import os

from pyramid_mailer.message import Message
from pyramid_mailer import get_mailer
from chameleon import PageTemplateLoader

from pyramid.events import subscriber

from mr.roboto.events import NewPush

templates = PageTemplateLoader(os.path.join(os.path.dirname(__file__), "templates"))


@subscriber(NewPush)
def send_mail_on_push(event):
    mailer = get_mailer(event.request)
    payload = event.payload
    # Send a mail
    if len(payload['commits']) < 40:
        # safeguard against github getting confused and sending us the entire history

        for commit in payload['commits']:

            short_commit_msg = commit['message'].split('\n')[0][:60]
            reply_to = '%s <%s>' % (commit['committer']['name'], commit['committer']['email'])
            diff = requests.get(commit['url'] + '.diff').content

            files = ['A %s' % f for f in commit['added']]
            files.extend('M %s' % f for f in commit['modified'])
            files.extend('D %s' % f for f in commit['removed'])

            data = {
                'push': payload,
                'commit': commit,
                'files': '\n'.join(files),
                'diff': diff,
            }

            msg = Message(
                subject='%s/%s: %s' % (payload['repository']['name'],
                                       payload['ref'].split('/')[-1],
                                       short_commit_msg),
                sender="%s <svn-changes@plone.org>" % commit['committer']['name'],
                #recipients=["plone-cvs@lists.sourceforge.net"],
                recipients=["ramon.nb@gmail.com", "contact@timostollenwerk.net", "david.glick@plone.org", "ericsteele47@gmail.com"],
                body=templates['commit_email.pt'](**data),
                extra_headers={'Reply-To': reply_to}
            )

            mailer.send(msg)
