# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatejenkins
from mr.roboto.views.run import add_log

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
    repo_object = request.registry.settings['github'].get_repo(repo)
    commit = repo_object.get_commit(commit_hash)
    comment_object = None
    old_message = ''
    for comment in commit.get_comments():
        if comment.user == 'mr.roboto@plone.org':
            comment_object = comment
            old_message = comment_object.body

    roboto_url = request.registry.settings['roboto_url']
    jk_job = answer['name']
    full_url = answer['build']['full_url']
    message = ''
    if answer['build']['phase'] == 'STARTED':
        #we just started the build
        add_log(request, 'jenkin', 'Commit to ' + repo + ' testing !')
        if old_message == '':
            message = "* " + jk_job + " at : " + full_url
        else:
            message = old_message + '\n' + "* " + jk_job + " at : " + full_url

    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'SUCCESS':
        # Great it worked
        add_log(request, 'jenkin', 'Commit to ' + repo + ' OK !')
        temp = old_message.split(jk_job)
        message = temp[0] + ' Success ![Alt text](' + roboto_url + '/static/roboto_si.png)' + temp[1]

    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'FAILURE':
        # Oooouu it failed
        add_log(request, 'jenkin', 'Commit to ' + repo + ' FAILED !')
        temp = old_message.split(jk_job)
        message = temp[0] + ' Fail ![Alt text](' + roboto_url + '/static/roboto_no.png)' + temp[1]
        
    if comment_object:
        comment_object.edit(message)
    else:
        commit.create_comment("Testing:\n" + message)


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
    commit_hash = request.GET['commit_hash']
    base = request.GET['base']
    module = request.GET['module']
    repo = base + '/' + module
    repo_object = request.registry.settings['github'].get_repo(repo)
    commit = repo_object.get_commit(commit_hash)
    jk_job = answer['name']
    roboto_url = request.registry.settings['roboto_url']
    full_url = answer['build']['full_url']
    if answer['build']['phase'] == 'STARTED':
        #we just started the build
        commit.create_comment('I\'m going to test this commit with ' + jk_job + ' you can check it at : ' + full_url + ', good luck!')
    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'SUCCESS':
        # Great it worked
        commit.create_comment('I tried your commit on the ' + jk_job + ' and the tests pass!! Congrats!! I own you a beer!! Share your achievment: ' + full_url + ' ![Alt text](' + roboto_url + '/static/roboto_si.png)')
    if answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'FAILURE':
        # Oooouu it failed
        commit.create_comment('I tried your commit on the ' + jk_job + ' and the tests does not pass!! Oups, maybe is not your fault and the tests where not passing before your commit!: ' + full_url + ' ![Alt text](' + roboto_url + '/static/roboto_no.png)')
