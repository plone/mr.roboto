# -*- coding: utf-8 -*-
from hashlib import sha1

import hmac
import json
import sys
import urllib
import urllib2


payload = {"forced": False, "compare": "https://github.com/plone/plone.app.multilingual/compare/781147b6b6a3...434a2f6ffdf4", "pusher": {"name": "none"}, "repository": {"fork": False, "watchers": 11, "description": "Plone multilingual plugin", "language": "Python", "has_downloads": True, "url": "https://github.com/plone/plone.app.multilingual", "master_branch": "master", "created_at": 1309424135, "private": False, "pushed_at": 1366796543, "open_issues": 1, "has_wiki": False, "organization": "plone", "owner": {"name": "plone", "email": None}, "has_issues": True, "forks": 20, "size": 596, "stargazers": 11, "id": 1977148, "name": "plone.app.multilingual"}, "created": False, "deleted": False, "commits": [{"committer": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "added": ["src/plone/app/multilingual/locales/fr/LC_MESSAGES/plone.app.multilingual.po"], "author": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "distinct": True, "timestamp": "2013-04-24T02:19:24-07:00", "modified": ["docs/HISTORY.txt"], "url": "https://github.com/plone/plone.app.multilingual/commit/d8eb770d9a0d0f406e9c14da9e10a3375cfe8922", "message": "Merge pull request #49 from savoirfairelinux/master\n\nAdded French translation", "removed": [], "id": "d8eb770d9a0d0f406e9c14da9e10a3375cfe8922"}, {"committer": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "added": [], "author": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "distinct": True, "timestamp": "2013-04-24T02:24:53-07:00", "modified": ["src/plone/app/multilingual/browser/edit.py"], "url": "https://github.com/plone/plone.app.multilingual/commit/e71d3d8250dfe652c59630384053988a8d9faf47", "message": "Solve bug #50", "removed": [], "id": "e71d3d8250dfe652c59630384053988a8d9faf47"}, {"committer": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "added": [], "author": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "distinct": True, "timestamp": "2013-04-24T02:42:21-07:00", "modified": ["docs/HISTORY.txt", "src/plone/app/multilingual/browser/edit.py"], "url": "https://github.com/plone/plone.app.multilingual/commit/434a2f6ffdf4f71b54106d6e720c7f7d597e43bb", "message": "Nicer #50 bug solution", "removed": [], "id": "434a2f6ffdf4f71b54106d6e720c7f7d597e43bb"}], "after": "434a2f6ffdf4f71b54106d6e720c7f7d597e43bb", "head_commit": {"committer": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "added": [], "author": {"username": "bloodbare", "name": "Ramon Navarro Bosch", "email": "ramon.nb@gmail.com"}, "distinct": True, "timestamp": "2013-04-24T02:42:21-07:00", "modified": ["docs/HISTORY.txt", "src/plone/app/multilingual/browser/edit.py"], "url": "https://github.com/plone/plone.app.multilingual/commit/434a2f6ffdf4f71b54106d6e720c7f7d597e43bb", "message": "Nicer #50 bug solution", "removed": [], "id": "434a2f6ffdf4f71b54106d6e720c7f7d597e43bb"}, "ref": "refs/heads/master", "before": "781147b6b6a3e819b48da50accced8472ae1552c"}
post = {"payload": json.dumps(payload)}


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print "We need 4 args"
        print "[secret] [host]"
        exit(0)

    url_values = urllib.urlencode(post)
    sha1_call = hmac.new(sys.argv[1], url_values, sha1).hexdigest()
    headers = {'User-Agent': 'mr.roboto', 'X-Hub_Signature': 'sha1=' + sha1_call}
    req = urllib2.Request(sys.argv[2], url_values, headers)
    # Call mr.roboto
    response = urllib2.urlopen(req)
    print response
