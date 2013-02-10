from lxml import etree
import StringIO
from plonejenkins.middleware.jobs import create_jenkins_job_xml


def jenkins_remove_job(request, pull_request):
    """
    Remove the jenkins job from this pull request
    """
    # look for the jenkins job and remove it
    ident = 'pull-request-' + pull_request
    request.jenkins.delete_job(ident)
    pass


def jenkins_pull_job(request, pull_request, branch=None, params=None):
    """
    Pull requests jenkins job
    """
    # We need to create the job with the checkout of the pull request
    ident = 'pull-request-' + pull_request

    if request.jenkins.job_exists(ident):
        request.jenkins.build_job(ident, params)

    else:
        url_to_callback = request.registry.settings['callback_url'] + 'corepull?pull=' + ident
        job_xml = create_jenkins_job_xml(
            'Pull Request ' + pull_request,
            '2.7',
            'no-reply@plone.org',
            git_branch=branch,
            url_to_callback=url_to_callback,
            pull=ident)
        # create a callback
        # upload to jenkins
        request.jenkins.create_job(ident, job_xml)
        request.jenkins.build_job(ident, params)
    info = request.jenkins.get_job_info(ident)
    return info.url


def jenkins_job(request, job, url_to_callback, params=None):
    """
    Generic jenkins call job
    """

    # First we check if the job exists
    if not request.jenkins.job_exists(job):
        # we create the job
        pass

    # We are going to reconfigure the job
    xml_config = request.jenkins.get_job_config(job)
    f = StringIO(xml_config)
    xml_object = etree.parse(f)
    endpoint = xml_object.parse('/project/properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty/endpoints/com.tikal.hudson.plugins.notification.Endpoint/url')
    if len(endpoint) == 1:
        endpoint.text = url_to_callback

    # We are going to add a publisher call to url

    # <properties>
    #   <com.tikal.hudson.plugins.notification.HudsonNotificationProperty plugin="notification@1.4">
    #     <endpoints>
    #       <com.tikal.hudson.plugins.notification.Endpoint>
    #         <protocol>HTTP</protocol>
    #         <url>http://localhost:6543/callback/corecommit?commit_hash=999</url>
    #       </com.tikal.hudson.plugins.notification.Endpoint>
    #     </endpoints>
    #   </com.tikal.hudson.plugins.notification.HudsonNotificationProperty>
    # </properties>

    xml_reconfig = etree.tostring(xml_object)
    request.jenkins.reconfig_job(job, xml_reconfig)

    request.jenkins.build_job(job, params)

