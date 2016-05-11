# -*- coding: utf-8 -*-
import pickle


def get_pickled_data(filename):
    return pickle.loads(open(filename).read())


def plone_versions_targeted(repo, branch, request):
    sources = get_pickled_data(request.registry.settings['sources_file'])
    try:
        return sources[(repo, branch)]
    except KeyError:
        return []
