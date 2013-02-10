from configparser import ConfigParser, ExtendedInterpolation
import git
import os
import re
from shutil import rmtree
from tempfile import mkdtemp
import logging

logger = logging.getLogger('plonejenkins.middleware')


class Source():

    def __init__(self, protocol=None, url=None, push_url=None, branch=None):
        self.protocol = protocol
        self.url = url
        self.push_url = push_url
        self.branch = branch

    def create_from_string(self, source_string):
        protocol, url, push_url, branch = \
            (lambda a, b, c=None, d=None: (a, b, c, d))(*source_string.split())
        self.protocol = protocol
        self.url = url
        if push_url is not None:
            self.push_url = push_url.split('=')[-1]
        if branch is None:
            self.branch = 'master'
        else:
            self.branch = branch.split('=')[-1]
        return self

    @property
    def path(self):
        if self.url:
            match = re.match('(\w+://)(.+@)*([\w\d\.]+)(:[\d]+){0,1}/(?P<path>.+(?=\.git))(\.git)', self.url)
            if match:
                return match.groupdict()['path']
        return None


class PloneCoreBuildout(object):
    PLONE_COREDEV_LOCATION = "git@github.com:plone/buildout.coredev.git"

    def __init__(self, core_version=None):
        self.core_version = core_version
        self.location = mkdtemp()
        self.repo = self._clone()
        self.sources = self._get_sources()
        self.versions = self._get_versions()

    def __del__(self):
        rmtree(self.location)

    def _clone(self):
        logger.info("Cloning github repository %s, branch=%s"\
                        % (self.location, self.core_version))
        git.Repo.clone_from(self.PLONE_COREDEV_LOCATION,
                            self.location,
                            branch=self.core_version,
                            depth=1)

    def _get_sources(self):
        logger.info("Parsing source information")
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.optionxform = str
        path = os.path.join(self.location, 'sources.cfg')
        config.readfp(open(path))
        sources_dict = {}
        for name, value in config['sources'].items():
            source = Source().create_from_string(value)
            sources_dict[name] = source
        return sources_dict

    def _get_versions(self):
        logger.info("Parsing version information")
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.optionxform = str
        path = os.path.join(self.location, 'versions.cfg')
        config.readfp(open(path))
        return config['versions']

    def get_package_branch(self, package_name):
        return self.sources[package_name].branch

    def get_package_version(self, package_name):
        return self.versions[package_name]
