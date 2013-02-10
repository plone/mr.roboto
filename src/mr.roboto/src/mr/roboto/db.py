# -*- encoding: utf-8 -*

import json


class ReposDB(object):

    def __init__(self, filename):
        self._filename = filename
        f = open(filename, 'w+')
        content = f.read()
        if content != '':
            self._db = json.loads(f.read())
        else:
            self._db = {}
        f.close()

    def save(self):
        f = open(self._filename, 'w+')
        f.write(json.dumps(self._db))
        f.close()

    def get(self):
        return self._db

    def add(self, egg, repo):
        self._db[egg] = {'kgs': '', 'github': repo}
        self.save()

    def delete(self, egg):
        del self._db[egg]
        self.save()


class PullsDB(object):

    def __init__(self, filename):
        self._filename = filename
        f = open(filename, 'w+')
        content = f.read()
        if content != '':
            self._db = json.loads(f.read())
        else:
            self._db = {}
        f.close()

    def save(self):
        f = open(self._filename, 'w+')
        f.write(json.dumps(self._db))
        f.close()

    def get(self, pull_id):
        return self._db.get(pull_id)

    def set(self, pull_id, jenkins_urls=[], seen_committers=[]):
        self._db[pull_id] = {'jenkins_urls': jenkins_urls, 'seen_committers': seen_committers}
        self.save()
        return {'jenkins_urls': jenkins_urls, 'seen_committers': seen_committers}

    def delete(self, pull_id):
        del self._db[pull_id]
        self.save()
