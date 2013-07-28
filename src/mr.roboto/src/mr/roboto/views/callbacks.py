# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatejenkins
from mr.roboto.views.run import add_log
import transaction
from pyramid_mailer import get_mailer
from chameleon import PageTemplateLoader
from pyramid_mailer.message import Message


callbackCommit = Service(name='Callback for commits', path='/callback/corecommit',
                    description="Callback for commits jobs on jenkins")

callbackPull = Service(name='Callback for pull requests', path='/callback/corepull',
                    description="Callback for pull request on jenkins")

templates = PageTemplateLoader(os.path.join(os.path.dirname(__file__), "templates"))

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


@callbackCommit.post()
def functionCallbackCommit(request):
    """
    For core-dev

    When jenkins is finished it calls this url
    {"name":"JobName",
     "url":"JobUrl",
     "build":{"number":1,
        "phase":"FINISHED",
        "status":"FAILED",
        "url":"job/project/5",
        "full_url":"http://ci.jenkins.org/job/project/5"
        "parameters":{"branch":"master"}
     }
    }

    We are going to write on the comment

    """
    answer = request.json_body
    jk_job_id = request.GET['jk_job_id']
    add_log(request, 'jenkin', 'Received job ' + jk_job_id)
    jobs = list(request.registry.settings['db']['jenkins_job'].find({'jk_uid': jk_job_id}))
    commit_hash = ''
    repo = ''
    who = ''
    branch = ''
    # We update the jk_url
    request.registry.settings['db']['jenkins_job'].update({'jk_uid': jk_job_id}, {'$set': {'jk_url': answer['build']['full_url']}})
    for job in jobs:
        # We set the job url
        commit_hash = job['ref']
        repo = job['repo']
        who = job['who']
        branch= job['branch']

    ghObject = request.registry.settings['github']

    jk_job = answer['name']
    full_url = answer['build']['full_url']

    if answer['build']['phase'] == 'STARTED':
        # We started the job so we are going to write on the GH commit
        # A line with the status
        add_log(request, 'jenkin', 'Commit %s to %s start testing %s ' % (commit_hash, repo, jk_job))
        message = "\n* %s - %s [PENDING] " % (jk_job, full_url)
        ghObject.add_commit_message(repo, commit_hash, message)

    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'SUCCESS':
        # Great it worked
        add_log(request, 'jenkin', 'Commit %s to %s OK %s ' % (commit_hash, repo, jk_job))
        # We can change the comment of the commit
        oldMessage = "%s [PENDING] " % full_url
        message = "%s [SUCCESS] " % full_url
        ghObject.replace_commit_message(repo, commit_hash, oldMessage, message)

    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'FAILURE':
        # Oooouu it failed

        # We send a mail to testbot saying that

        data = {
            'repo': repo,
            'hash': commit_hash,
            'branch': branch,
            'name': who,
            'jk-job': jk_job,
            'jk-url': full_url
        }

        mailer = get_mailer(request)
        msg = Message(
            subject='%s %s: %s' % (job, repo, "Broken tests results"),
            sender="Jenkins Job FAIL <jenkins@plone.org>" 
            recipients=["plone-testbot@lists.plone.org"],
            body=templates['broken_job.pt'](**data),
            extra_headers={'Reply-To': who}
        )

        mailer.send_immediately(msg, fail_silently=False)

        add_log(request, 'jenkin', 'Commit %s to %s FAIL %s ' % (commit_hash, repo, jk_job))
        # We can change the comment of the commit
        oldMessage = "%s [PENDING] " % full_url
        message = "%s [FAIL] " % full_url
        ghObject.replace_commit_message(repo, commit_hash, oldMessage, message)

    transaction.commit()

