# -*- encoding: utf-8 -*

import json
import persistent
import datetime
from mongopersist import mapping


class PLIPPackage(persistent.Persistent):
    """ PLIP Testing representation """
    _p_mongo_collection = 'plip'

    def __init__(
            self,
            repo=None,
            branch=None,
            buildout=None,
            description=None,
            url=None,
            buildout_branch=None,
            buildout_file=None,
            jk_url="",
            contact=None):
        self.repo = repo
        self.branch = branch
        self.buildout = buildout
        self.buildout_file = buildout_file
        self.buildout_branch = buildout_branch
        self.description = description
        self.url = url
        self.contact = contact
        self.jk_url = jk_url


class PLIPPackages(mapping.MongoCollectionMapping):
    __mongo_collection__ = 'plip'
    __mongo_mapping_key__ = 'description'


class JenkinsJob(persistent.Persistent):
    """ Jenkins Job Testing representation """
    _p_mongo_collection = 'jenkins_job'

    def __init__(
            self,
            job_type,
            jk_uid,
            repo=None,
            branch=None,
            plone_version=None,
            who=None,
            ref=None,
            jk_name=None,
            jk_url=None):
        self.type = job_type
        self.repo = repo
        self.branch = branch
        self.plone_version = plone_version
        self.date = str(datetime.datetime.now())
        self.jk_uid = jk_uid
        self.who = who
        self.jk_name = jk_name
        self.ref = ref
        self.jk_url = jk_url


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
