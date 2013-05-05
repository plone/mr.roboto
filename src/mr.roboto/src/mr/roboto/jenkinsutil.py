from lxml import etree
from StringIO import StringIO
from mr.roboto.jobs import create_jenkins_job_xml
import urllib2
import urllib
import json


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


def jenkins_job_external(request, job, callback_url, data, payload=None, params=None):
    """
    Generic plone project job
    """

    jenkins = request.registry.settings['jenkins']

    if not jenkins.job_exists(job):
        # If we have job information we apply

        job_xml = create_jenkins_job_xml(
            'Test %s' % data['description'],
            '2.7',
            data['contact'],
            git_url=data['buildout'],
            git_branch=data['buildout_branch'] if data['buildout_branch'] else 'master',
            callback_url=callback_url,
            command=data['buildout_file'])

        jenkins.create_job(job, job_xml)

    else:
        # We reconfigure job
        xml_config = jenkins.get_job_config(job)
        if xml_config is None:
            return
        f = StringIO(xml_config)
        xml_object = etree.parse(f)
        isthere = xml_object.xpath('/project/properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty')
        # We are going to add a publisher call to url
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

        # Reconfigure the job
        xml_reconfig = etree.tostring(xml_object)
        jenkins.reconfig_job(job, xml_reconfig)

    url = jenkins.build_job_url(job, parameters=params)

    spayload = json.dumps(payload)
    sending_payload = {'payload': spayload}

    jenkins.jenkins_open(urllib2.Request(url, urllib.urlencode(sending_payload)))


def jenkins_core_job(request, job, callback_url, params=None, payload=None):
    """
    Generic jenkins core job
    """

    jenkins = request.registry.settings['jenkins']

    # First we check if the job exists
    if not jenkins.job_exists(job):
        # we  don't create the job
        return

    # We are going to reconfigure the job to add the notification
    xml_config = jenkins.get_job_config(job)
    if xml_config is None:
        return
    f = StringIO(xml_config)
    xml_object = etree.parse(f)
    isthere = xml_object.xpath('/project/properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty')
    # We are going to add a publisher call to url
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

    # Reconfigure the job
    xml_reconfig = etree.tostring(xml_object)
    jenkins.reconfig_job(job, xml_reconfig)

    #jenkins.build_job(job, params)
    url = jenkins.build_job_url(job, parameters=params)

    spayload = json.dumps(payload)
    sending_payload = {'payload': spayload}

    jenkins.jenkins_open(urllib2.Request(url, urllib.urlencode(sending_payload)))

