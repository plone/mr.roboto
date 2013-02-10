
from pyramid.renderers import render


def create_jenkins_job_xml(display_name,
                           python_version,
                           email_notification_recipients,
                           buildout='jenkins.cfg',
                           node='Slave',
                           git_branch=None,
                           git_url='git://github.com/plone/buildout.coredev.git',
                           callback_url=None,
                           pull=None):

    command = "%s bootstrap.py\n" % python_version
    command += "bin/buildout -c %s\n" % buildout

    command += "bin/jenkins-alltests -1"

    result = render('mr.roboto:templates/plone.pt',
                    {'callback_url': callback_url,
                     'display_name': display_name,
                     'email_notification_recipients': email_notification_recipients,
                     'git_url': git_url,
                     'git_branch': git_branch,
                     'node': node,
                     'command': command})

    return result
