# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatejenkins
from mr.roboto.views.run import add_log
import transaction
from pyramid_mailer import get_mailer
from chameleon import PageTemplateLoader
from pyramid_mailer.message import Message
import os
from mr.roboto import templates



callbackCommit = Service(name='Callback for commits', path='/callback/corecommit',
                    description="Callback for commits jobs on jenkins")

callbackPull = Service(name='Callback for pull requests', path='/callback/corepull',
                    description="Callback for pull request on jenkins")


@callbackPull.post()
@validatejenkins
def functionCallbackPull(request):
    """
    When jenkins is finished it calls this url
    {"name":"JobName",
     "url":"JobUrl",
     "build":{"number":1,
        "phase":"STARTED",
        "status":"FAILED",
        "url":"job/project/5",
        "full_url":"http://ci.jenkins.org/job/project/5"
        "parameters":{"branch":"master"}
     }
    }

    We are going to write on the comment

    """
    answer = request.json_body
    pull_number = request.GET['pull']
    pull = request.registry.settings['github'].get_pull(pull_number)
    jk_job = answer['name']
    full_url = answer['full_url']
    if answer['build']['phase'] == 'STARTED':
        #we just started the build
        pull.create_comment('I\'m going to test this pull with ' + jk_job + ' you can check it at : ' + full_url + ', good luck!')
    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'SUCCESS':
        # Great it worked
        pull.create_comment('I tried your pull request on the ' + jk_job + ' and the tests pass!! Congrats!! I own you a beer!! Share your achievment: ' + full_url)
    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'FAILURE':
        # Oooouu it failed
        pull.create_comment('I tried your pull request on the ' + jk_job + ' and the tests does not pass!! Oups, maybe is not your fault and the tests where not passing without your pull request!: ' + full_url)
    # TODO we can create a comment hook
