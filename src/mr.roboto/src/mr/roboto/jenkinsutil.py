from lxml import etree
from StringIO import StringIO
from mr.roboto.jobs import create_jenkins_job_xml


def jenkins_remove_job(request, identifier):
    """
    Remove the jenkins job from this pull request
    """
    jenkins = request.registry.settings['jenkins']
    jenkins.delete_job(identifier)


def jenkins_build_job(request, identifier, params=None):
    jenkins = request.registry.settings['jenkins']
    jenkins.build_job(identifier, params)


def jenkins_get_job_url(request, identifier):
    jenkins = request.registry.settings['jenkins']
    info = jenkins.get_job_info(identifier)
    return info['url']


def jenkins_create_pull_job(request, pull_request, branch=None, params=None):
    """
    Pull requests jenkins job
    """

    jenkins = request.registry.settings['jenkins']

    # We need to create the job with the checkout of the pull request
    ident = 'pull-request-%s' % pull_request
    if branch:
        ident = '%s-%s' % (ident, branch)
    if not jenkins.job_exists(ident):
        callback_url = request.registry.settings['callback_url'] + 'corepull?pull=' + ident
        job_xml = create_jenkins_job_xml(
            'Pull Request %s' % pull_request,
            '2.7',
            'no-reply@plone.org',
            git_branch=branch,
            callback_url=callback_url,
            pull=ident)
        # create a callback
        # upload to jenkins
        jenkins.create_job(ident, job_xml)

    return ident


def jenkins_job_external(request, job, callback_url, repo, branch=None, params=None):
    """
    Generic plone project job
    """

    jenkins = request.registry.settings['jenkins']

    # First we check if the job exists
    if not jenkins.job_exists(job):

        # we create the job
        job_xml = create_jenkins_job_xml(
            'Test %s' % repo,
            '2.7',
            'no-reply@plone.org',
            git_url=repo,
            git_branch=branch if branch else 'master',
            callback_url=callback_url)

        jenkins.create_job(job, job_xml)

    jenkins.build_job(job, params)


def jenkins_job(request, job, callback_url, params=None):
    """
    Generic jenkins call job
    """

    jenkins = request.registry.settings['jenkins']

    # First we check if the job exists
    if not jenkins.job_exists(job):
        # we create the job
        pass

    # We are going to reconfigure the job
    xml_config = jenkins.get_job_config(job)
    f = StringIO(xml_config)
    xml_object = etree.parse(f)
    isthere = xml_object.xpath('/project/properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty')
    if len(isthere) == 0:
        properties = xml_object.xpath('/project/properties')
        listener = """<com.tikal.hudson.plugins.notification.HudsonNotificationProperty plugin="notification@1.4">
         <endpoints>
          <com.tikal.hudson.plugins.notification.Endpoint>
           <protocol>HTTP</protocol>
           <url></url>
          </com.tikal.hudson.plugins.notification.Endpoint>
         </endpoints>
        </com.tikal.hudson.plugins.notification.HudsonNotificationProperty>
        """
        xml_list = etree.XML(listener)
        xml_list.xpath('/com.tikal.hudson.plugins.notification.HudsonNotificationProperty/endpoints/com.tikal.hudson.plugins.notification.Endpoint/url')[0].text = callback_url
        properties.append(xml_list)
    else:
        endpoint = xml_object.xpath('/project/properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty/endpoints/com.tikal.hudson.plugins.notification.Endpoint/url')
        if len(endpoint) == 1:
            endpoint[0].text = callback_url

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
    jenkins.reconfig_job(job, xml_reconfig)

    jenkins.build_job(job, params)

