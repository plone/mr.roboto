
from pyramid.renderers import render


def create_jenkins_job_xml(displayname,
                           python_version,
                           email_notification_recipients,
                           buildout='jenkins.cfg',
                           node='Slave',
                           git_branch=None,
                           git_url='git://github.com/plone/buildout.coredev.git',
                           url_to_callback=None,
                           pull=None):

    command = "%s bootstrap.py\n" % python_version
    command += "bin/buildout -c %s" % buildout


    command += "bin/jenkins-alltests -1"


    result = render('plonejenkins.middleware:templates/plone.xml',
        {'url_to_callback': url_to_callback,
         'displayName': displayname,
         'email_notification_recipients': email_notification_recipients,
         'git_url': git_url,
         'git_branch': git_branch})

    return result