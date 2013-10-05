# -*- encoding: utf-8 -*

import json
import persistent
import datetime
from mongopersist import mapping
from uuid import uuid4


class PLIPPackage(persistent.Persistent):
    """ PLIP Testing representation """
    _p_mongo_collection = 'plip'

    def __init__(
            self,
            repo=None,
            buildout=None,
            description=None,
            url=None,
            buildout_branch=None,
            buildout_file=None,
            jk_url="",
            contact=None,
            robot_tests=None):
        self.repo = repo
        self.buildout = buildout
        self.buildout_file = buildout_file
        self.buildout_branch = buildout_branch
        self.description = description
        self.url = url
        self.contact = contact
        self.jk_url = jk_url
        self.robot_tests = robot_tests


class PLIPPackages(mapping.MongoCollectionMapping):
    __mongo_collection__ = 'plip'
    __mongo_mapping_key__ = 'description'


class Push(persistent.Persistent):
    """ 
    Push to plone github 

    repo : has the repository where we pushed
    branch : branch where we did the push
    internal_identifier : identifier of the push
    data : list of all commits

    data is a list of :
    [
        {
            'diff': diff,
            'files': files,
            'short_commit_msg': commit_msg,
            'reply_to': who,
            'sha': sha
        }
    ]

    """
    _p_mongo_collection = 'push'

    def __init__(
            self,
            internal_identifier,
            data,
            who=None,
            repo=None,
            branch=None,
            payload=None):
        self.payload = payload
        self.data = data
        self.who = who
        self.repo = repo
        self.branch = branch
        self.date = str(datetime.datetime.now())
        self.internal_identifier = internal_identifier


class Pushes(mapping.MongoCollectionMapping):
    __mongo_collection__ = 'push'
    __mongo_mapping_key__ = 'internal_identifier'


class JenkinsJob(persistent.Persistent):
    """ 
    Jenkins Job Testing representation 

    job_type : ['core', 'plip', 'corepackage']
    jk_uid : identifier of the job -> [push_id]_[jk_name] or [package]_[push_id]_[jk_name]
    date : when we started
    ref : reference to the push
    jk_name : name of the jenkins job
    jk_url : url of the build (added on callback)
    result : [None, True, False] depending on the result of the job (added on callback)

    """
    _p_mongo_collection = 'jenkins_job'

    def __init__(
            self,
            job_type,
            jk_uid,
            push=None,
            jk_name=None,
            jk_url=None,
            result=None):
        self.type = job_type
        self.date = str(datetime.datetime.now())
        self.jk_uid = jk_uid
        self.jk_name = jk_name
        self.push = push
        self.jk_url = jk_url
        self.result = result


class JenkinsJobs(mapping.MongoCollectionMapping):
    __mongo_collection__ = 'jenkins_job'
    __mongo_mapping_key__ = 'jk_uid'


class CorePackage(persistent.Persistent):
    """ CORE Package representation """
    _p_mongo_collection = 'core_package'

    def __init__(
            self,
            name,
            repo,
            branch,
            plone_version):
        self.name = name
        self.repo = repo
        self.branch = branch
        self.plone_version = plone_version
        self.ident = repo + ':' + branch + ':' + plone_version

    def __str__(self):
        return self.ident

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self)


class CorePackages(mapping.MongoCollectionMapping):
    __mongo_collection__ = 'core_package'
    __mongo_mapping_key__ = 'ident'


class PullsDB(object):

    def __init__(self, filename):
        self._filename = filename
        f = open(filename, 'r')
        content = f.read()
        if content != '':
            self._db = json.loads(content)
        else:
            self._db = {}
        f.close()

    def save(self):
        f = open(self._filename, 'w+')
        f.write(json.dumps(self._db))
        f.close()

    def get(self, pull_id):
        return self._db.get(pull_id)

    def set(self, pull_id, jenkins_jobs=[], seen_committers=[]):
        self._db[pull_id] = {'jenkins_jobs': jenkins_jobs, 'seen_committers': seen_committers}
        self.save()
        return {'jenkins_jobs': jenkins_jobs, 'seen_committers': seen_committers}

    def delete(self, pull_id):
        del self._db[pull_id]
        self.save()
