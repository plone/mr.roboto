# -*- coding: utf-8 -*-
from collections import OrderedDict
from collections import UserDict
from configparser import ConfigParser
from configparser import ExtendedInterpolation
from tempfile import mkdtemp

import git
import logging
import os
import pickle
import re
import shutil


logger = logging.getLogger('mr.roboto')

PATH_RE = re.compile(
    r'(\w+://)(.+@)*([\w\d\.]+)(:[\d]+){0,1}/(?P<path>.+(?=\.git))(\.git)'
)


class Source(object):
    def __init__(self, protocol=None, url=None, push_url=None, branch=None):
        self.protocol = protocol
        self.url = url
        self.pushurl = push_url
        self.branch = branch

    def create_from_string(self, source_string):
        source_parts = source_string.split()
        self.protocol = source_parts[0]
        self.url = source_parts[1]
        for param in source_parts[2:]:
            if param is not None:
                key, value = param.split('=')
                if key != 'path':
                    setattr(self, key, value)
        if self.pushurl is not None:
            # I doubt this is needed, should be handled already with
            # param.split above.
            self.pushurl = self.pushurl.split('=')[-1]
        if self.branch is None:
            self.branch = 'master'
        else:
            # I doubt this is needed, should be handled already with
            # param.split above.
            self.branch = self.branch.split('=')[-1]
        return self

    @property
    def path(self):
        if self.url:
            match = PATH_RE.match(self.url)
            if match:
                return match.groupdict()['path']
        return None  # pragma: no cover


class SourcesFile(UserDict):
    def __init__(self, file_location):
        self.file_location = file_location
        self._data = None

    @property
    def data(self):
        if self._data:
            return self._data
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.optionxform = str
        with open(self.file_location) as f:
            config.read_file(f)
        # Insert buildout:directory, as workaround for
        # https://github.com/plone/mr.roboto/issues/82
        config["buildout"]["directory"] = os.getcwd()
        sources_dict = OrderedDict()
        for name, value in config['sources'].items():
            source = Source().create_from_string(value)
            sources_dict[name] = source
        self._data = sources_dict
        return self._data

    def __iter__(self):
        return self.data.__iter__()


class CheckoutsFile(UserDict):
    def __init__(self, file_location):
        self.file_location = file_location
        self._data = None

    @property
    def data(self):
        if self._data:
            return self._data  # pragma: no cover
        config = ConfigParser(interpolation=ExtendedInterpolation())
        with open(self.file_location) as f:
            config.read_file(f)
        checkouts = config.get('buildout', 'auto-checkout')
        checkout_list = checkouts.split('\n')
        self._data = checkout_list
        return self._data


class PloneCoreBuildout(object):
    PLONE_COREDEV_LOCATION = 'git://github.com/plone/buildout.coredev.git'

    def __init__(self, core_version=None):
        self.core_version = core_version
        self.location = mkdtemp()
        self.clone()
        self.sources = SourcesFile(f'{self.location}/sources.cfg')
        self.checkouts = CheckoutsFile(f'{self.location}/checkouts.cfg')

    def clone(self):
        logger.info(
            f'Commit: cloning github repository {self.location}, '
            f'branch={self.core_version}'
        )
        git.Repo.clone_from(
            self.PLONE_COREDEV_LOCATION,
            self.location,
            branch=self.core_version,
            depth=1,
        )

    def cleanup(self):
        shutil.rmtree(self.location)


def get_sources_and_checkouts(request):
    """Get sources.cfg and checkouts.cfg from buildout.coredev

    Get them for all major plone releases
    (see plone_versions on mr.roboto's configuration),
    process and store their data on pickle files for later usage.
    """
    sources_dict = {}
    checkouts_dict = {}

    actual_plone_versions = request.registry.settings['plone_versions']

    for plone_version in actual_plone_versions:
        logger.info(
            f'Commit: checking sources and checkouts ' f'from plone {plone_version}'
        )
        buildout = PloneCoreBuildout(plone_version)

        for source in buildout.sources:
            source_obj = buildout.sources[source]
            if source_obj.path:
                key = (source_obj.path, source_obj.branch)
                if key not in sources_dict:
                    sources_dict[key] = [plone_version]
                else:
                    sources_dict[key].append(plone_version)
            else:
                logger.warning(f'Package {source} does not have a valid URL')  # pragma: no cover

        checkouts_dict[plone_version] = []
        for checkout in buildout.checkouts.data:
            if checkout:
                checkouts_dict[plone_version].append(checkout)

        buildout.cleanup()

    sources_file = request.registry.settings['sources_file']
    with open(sources_file, 'bw') as sf:
        sf.write(pickle.dumps(sources_dict))

    checkouts_file = request.registry.settings['checkouts_file']
    with open(checkouts_file, 'bw') as sf:
        sf.write(pickle.dumps(checkouts_dict))
