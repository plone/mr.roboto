# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatejenkins
from mr.roboto.views.run import add_log
import transaction

callbackCommit = Service(name='Callback for commits', path='/callback/corecommit',
                    description="Callback for commits jobs on jenkins")

callbackPull = Service(name='Callback for pull requests', path='/callback/corepull',
                    description="Callback for pull request on jenkins")

callbackPlone = Service(name='Callback for commits on plone external repo', path='/callback/plonecommit',
                    description="Callback for pull request on jenkins")


@callbackPlone.post()
@validatejenkins
def functionCallbackPloneCommit(request):
    """
    For NON core-dev

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
    commit_hash = request.GET['commit_hash']
    base = request.GET['base']
    module = request.GET['module']
    repo = base + '/' + module
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
        add_log(request, 'jenkin', 'Commit %s to %s FAIL %s ' % (commit_hash, repo, jk_job))
        # We can change the comment of the commit
        oldMessage = "%s [PENDING] " % full_url
        message = "%s [FAIL] " % full_url
        ghObject.replace_commit_message(repo, commit_hash, oldMessage, message)


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
    jobs = list(request.registry.settings['db']['jenkins_job'].find({'jk_job_id': jk_job_id}))
    commit_hash = ''
    for job in jobs:
        commit_hash = job['ref']
    base = request.GET['base']
    module = request.GET['module']
    repo = base + '/' + module
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
        add_log(request, 'jenkin', 'Commit %s to %s FAIL %s ' % (commit_hash, repo, jk_job))
        # We can change the comment of the commit
        oldMessage = "%s [PENDING] " % full_url
        message = "%s [FAIL] " % full_url
        ghObject.replace_commit_message(repo, commit_hash, oldMessage, message)

    transaction.commit()

