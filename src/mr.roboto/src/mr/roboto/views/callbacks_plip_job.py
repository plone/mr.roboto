# -*- encoding: utf-8 -*-
from cornice import Service
from mr.roboto.security import validatejenkins
from mr.roboto.views.run import add_log
import transaction
from pyramid_mailer import get_mailer
from chameleon import PageTemplateLoader
from pyramid_mailer.message import Message
import os
from mr.roboto import templates, dir_for_kgs
from mr.roboto.db import JenkinsJobs


callbackCommit = Service(name='Callback for plip commits', path='/callback/plipcommit',
                    description="Callback for plip commits jobs on jenkins")


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
    We are going to store a KGS if it passes the test

    """
    answer = request.json_body

    # get the information of the job that has the commit
    # commit_uuid_jobname
    jk_job_id = request.GET['jk_job_id']
    add_log(request, 'jenkin', 'Received job ' + jk_job_id)

    # get the job
    jenkins_jobs = JenkinsJobs(request.registry.settings['dm'])
    # get the job
    try:
        job = jenkins_jobs[jk_job_id]
    except KeyError:
        add_log(request, 'jenkin', 'Invalid plip jenkins job  %s ' % (jk_job_id))
        return

    # get the pushid
    push_uuid = job.push

    # get the job name
    jk_job = answer['name']

    # get the job url
    full_url = answer['build']['full_url']

    # We update the jk_url
    request.registry.settings['db']['jenkins_job'].update({'jk_uid': jk_job_id}, {'$set': {'jk_url': full_url}})

    # get the push object
    pushs = list(request.registry.settings['db']['push'].find({'internal_identifier': push_uuid}))
    if len(pushs) == 0:
        add_log(request, 'jenkin', 'No push linked to  %s ' % (push_uuid))
        return
    push = pushs[0]

    # get the repo
    repo = push['repo']

    # get the branch
    branch = push['branch']

    # get who did the push
    who = push['who']

    # get github and jenkinsapi objects
    ghObject = request.registry.settings['github']
    jkapiObject = request.registry.settings['jenkinsapi']

    if answer['build']['phase'] == 'STARTED':
        # we started a job so don't do anything
        add_log(request, 'jenkin', 'Push %s from %s to %s/%s start testing %s ' % (push_uuid, who, repo, branch, jk_job))

    elif answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'SUCCESS':
        # a job finished success
        add_log(request, 'jenkin', 'Push %s from %s to %s/%s on job %s OK' % (push_uuid, who, repo, branch, jk_job))

        # Update the result of the job on DB
        request.registry.settings['db']['jenkins_job'].update({'jk_uid': jk_job_id}, {'$set': {'result': True}})
        transaction.commit()

        # check if there is any other job working
        all_jobs = list(request.registry.settings['db']['jenkins_job'].find({'push': push_uuid, 'type': 'plip'}))

        completed = True
        all_green = True
        message = ''
        for j in all_jobs:
            message += j['jk_name'] + ' '
            if j['result'] is None:
                # We still miss some jobs
                completed = False
                message += '[PENDING]\n'
            elif j['result'] is True:
                message += '[SUCCESS]\n'
            elif j['result'] is False:
                all_green = False
                message += '[FAILURE]\n'

        # url for more information
        url = request.registry.settings['roboto_url'] + 'get_info?push=' + push_uuid

        # We need to setup the status of the commit
        if completed:
            # update commit GH
            if all_green:
                status = 'success'
                # Store the new KGS
                status_message = 'Mr. Roboto aproves this commit!'
                comment_message = 'TESTS PASSED\n Mr.Roboto url : %s\n %s' % (url, message)


            else:
                status = 'failure'
                status_message = 'Mr. Roboto does NOT aprove this commit!'
                comment_message = 'TESTS FAILED\n Mr.Roboto url : %s\n %s' % (url, message)
        else:
            status = 'pending'
            status_message = 'Mr. Roboto is still working!'


    elif answer['build']['phase'] == 'FINISHED' and answer['build']['status'] == 'FAILURE':
        # Oooouu it failed
        add_log(request, 'jenkin', 'Push %s from %s to %s/%s on job %s FAILED' % (push_uuid, who, repo, branch, jk_job))

        # Update the result of the job on DB
        request.registry.settings['db']['jenkins_job'].update({'jk_uid': jk_job_id}, {'$set': {'result': False}})
        transaction.commit()

        # check if there is any other job working
        all_jobs = list(request.registry.settings['db']['jenkins_job'].find({'push': push_uuid, 'type': 'plip'}))

        # look for if it's completed
        completed = True
        message = ''
        for j in all_jobs:
            message += j['jk_name'] + ' '
            if j['result'] is None:
                # We still miss some jobs
                completed = False
                message += '[PENDING]\n'
            elif j['result'] is True:
                message += '[SUCCESS]\n'
            elif j['result'] is False:
                message += '[FAILURE]\n'

        url = request.registry.settings['roboto_url'] + 'get_info?push=' + push_uuid

        # We need to setup the status of the commit
        if completed:
            # update commits GH
            status = 'failure'
            status_message = 'Mr. Roboto does NOT aprove this commit!'
            comment_message = 'TESTS FAILED\n Mr.roboto url : %s\n %s' % (url, message)

        else:
            status = 'pending'
            status_message = 'Mr. Roboto is still working!'


