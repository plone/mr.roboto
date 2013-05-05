
from pyramid.renderers import render

CORE_DEV_GIT_URL = 'git://github.com/plone/buildout.coredev.git'


def create_jenkins_job_xml(display_name,
                           python_version,
                           email_notification_recipients,
                           buildout='jenkins.cfg',
                           node='Slave',
                           git_branch=None,
                           git_url=CORE_DEV_GIT_URL,
                           callback_url=None,
                           pull=None,
                           command=None):

    if not command:
        command = "python%s bootstrap.py\n" % python_version
        command += "bin/buildout -c %s\n" % buildout
        # We need to do a checkout of the pull request

        if git_url != CORE_DEV_GIT_URL:
            command += "bin/jenkins-test"
        else:
            command += "bin/jenkins-alltests -1"

    result = render('mr.roboto:templates/plone.pt',
                    {'callback_url': callback_url,
                     'display_name': display_name,
                     'email_notification_recipients': email_notification_recipients,
                     'git_url': git_url,
                     'git_branch': git_branch,
                     'node': node,
                     'command': command,
                     'dollar': '$'})

    return result
