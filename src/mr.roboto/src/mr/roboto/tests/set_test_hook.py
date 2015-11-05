# -*- coding: utf-8 -*-
from github import Github

import sys


if __name__ == '__main__':

    if len(sys.argv) < 5:
        print "We need 4 args"
        print "[GH user] [GH passwd] [secret] [host]"
        exit(0)

    gh = Github(sys.argv[1], sys.argv[2], user_agent='PyGithub/Python')
    import pdb; pdb.set_trace()
    gh_repo = gh.get_repo('plone/plone.app.multilingual')

    commit_url = sys.argv[4] + 'run/corecommit'
    pull_url = sys.argv[4] + 'run/pullrequest'

    gh_repo.create_hook('web', {'url': commit_url, 'secret': sys.argv[3]}, 'push', True)
    gh_repo.create_hook('web', {'url': pull_url, 'secret': sys.argv[3]}, 'pull_request', True)
