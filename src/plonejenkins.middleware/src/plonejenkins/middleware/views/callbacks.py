# -*- encoding: utf-8 -*-
from cornice import Service
from plonejenkins.middleware.security import validatejenkins

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
    pull_number = request.GET('pull')
    pull = request.registry.settings['github'].get_pull(pull_number)
    jk_job = answer['name']
    full_url = answer['full_url']
    if answer['build']['phase'] == 'STARTED':
        #we just started the build
        pull.create_comment('I\'m going to test this pull with ' + jk_job + ' you can check it at : ' + full_url + ', good luck!')
    if answer['build']['phase'] == 'COMPLETED' and answer['build']['status'] == 'SUCCESS':
        # Great it worked
        pull.create_comment('I tried your pull request on the ' + jk_job + ' and the tests pass!! Congrats!! I own you a beer!! Share your achievment: ' + full_url)
    if answer['build']['phase'] == 'COMPLETED' and answer['build']['status'] == 'FAILED':
        # Oooouu it failed
        pull.create_comment('I tried your pull request on the ' + jk_job + ' and the tests does not pass!! Oups, maybe is not your fault and the tests where not passing without your pull request!: ' + full_url)
    # TODO we can create a comment hook

@callbackCommit.post()
@validatejenkins
def functionCallbackCommit(request):
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
    #import pdb; pdb.set_trace()
    answer = request.json_body
    commit_hash = request.GET('commit_hash')
    commit = request.registry.settings['github'].get_commit(commit_hash)
    jk_job = answer['name']
    full_url = answer['full_url']
    if answer['build']['phase'] == 'STARTED':
        #we just started the build
        commit.create_comment('I\'m going to test this commit with ' + jk_job + ' you can check it at : ' + full_url + ', good luck!')
    if answer['build']['phase'] == 'COMPLETED' and answer['build']['status'] == 'SUCCESS':
        # Great it worked
        commit.create_comment('I tried your commit on the ' + jk_job + ' and the tests pass!! Congrats!! I own you a beer!! Share your achievment: ' + full_url)
    if answer['build']['phase'] == 'COMPLETED' and answer['build']['status'] == 'FAILED':
        # Oooouu it failed
        commit.create_comment('I tried your commit on the ' + jk_job + ' and the tests does not pass!! Oups, maybe is not your fault and the tests where not passing before your commit!: ' + full_url)

    # We connect to github to write something about this commits
    # /repos/plone/:repo/commits/:sha/comments