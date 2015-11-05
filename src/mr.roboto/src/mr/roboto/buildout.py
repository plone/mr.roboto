# -*- coding: utf-8 -*-
from collections import OrderedDict
from configparser import ConfigParser
from configparser import ExtendedInterpolation
from tempfile import mkdtemp
from UserDict import UserDict

import git
import logging
import os
import re


logger = logging.getLogger('mr.roboto')


class Source(object):

    def __init__(self, protocol=None, url=None, push_url=None, branch=None):
        self.protocol = protocol
        self.url = url
        self.push_url = push_url
        self.branch = branch

    def create_from_string(self, source_string):
        protocol, url, extra_1, extra_2, extra_3 = (
            lambda a, b, c=None, d=None, e=None: (a, b, c, d, e))(*source_string.split())
        for param in [extra_1, extra_2, extra_3]:
            if param is not None:
                key, value = param.split('=')
                setattr(self, key, value)
        self.protocol = protocol
        self.url = url
        if self.push_url is not None:
            self.push_url = self.push_url.split('=')[-1]
        if self.branch is None:
            self.branch = 'master'
        else:
            self.branch = self.branch.split('=')[-1]
        return self

    @property
    def path(self):
        if self.url:
            match = re.match(
                '(\w+://)(.+@)*([\w\d\.]+)(:[\d]+){0,1}/(?P<path>.+(?=\.git))(\.git)', self.url)
            if match:
                return match.groupdict()['path']
        return None


class VersionsFile(object):

    def __init__(self, file_location):
        self.file_location = file_location

    @property
    def versions(self):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        with open(self.file_location) as f:
            config.readfp(f)
        return config['versions']

    def __contains__(self, package_name):
        return package_name.lower() in self.versions.keys()

    def __getitem__(self, package_name):
        if self.__contains__(package_name):
            return self.versions.get(package_name)
        else:
            raise KeyError

    def __setitem__(self, package_name, new_version):
        path = os.path.join(os.getcwd(), self.file_location)
        with open(path, 'r') as f:
            versionstxt = f.read()

        if package_name not in self:
            newline = "{} = {}".format(package_name, new_version)
            versionstxt += newline

        reg = re.compile("(^%s[\s\=]+)[0-9\.abrc]+" % package_name, re.MULTILINE)
        newVersionsTxt = reg.sub(r"\g<1>%s" % new_version, versionstxt)
        with open(path, 'w') as f:
            f.write(newVersionsTxt)

    def get(self, package_name):
        return self.__getitem__(package_name)

    def set(self, package_name, new_version):
        return self.__setitem__(package_name, new_version)


class SourcesFile(UserDict):

    def __init__(self, file_location):
        self.file_location = file_location

    @property
    def data(self):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.optionxform = str
        with open(self.file_location) as f:
            config.readfp(f)
        sources_dict = OrderedDict()
        for name, value in config['sources'].items():
            source = Source().create_from_string(value)
            sources_dict[name] = source
        return sources_dict

    def __setitem__(self, package_name, value):
        raise NotImplementedError

    def __iter__(self):
        return self.data.__iter__()


class CheckoutsFile(UserDict):

    def __init__(self, file_location):
        self.file_location = file_location

    @property
    def data(self):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        with open(self.file_location) as f:
            config.readfp(f)
        checkouts = config.get('buildout', 'auto-checkout')
        checkout_list = checkouts.split('\n')
        return checkout_list

    def __contains__(self, package_name):
        return package_name in self.data

    def __setitem__(self, package_name, enabled=True):
        path = os.path.join(os.getcwd(), self.file_location)
        with open(path, 'r') as f:
            checkoutstxt = f.read()
        with open(path, 'w') as f:
            if enabled:
                fixes_text = "# Test fixes only"
                reg = re.compile("^[\s]*%s\n" % fixes_text, re.MULTILINE)
                newCheckoutsTxt = reg.sub('    %s\n%s\n' %
                                          (package_name, fixes_text), checkoutstxt)
            else:
                reg = re.compile("^[\s]*%s\n" % package_name, re.MULTILINE)
                newCheckoutsTxt = reg.sub('', checkoutstxt)
            f.write(newCheckoutsTxt)

    def __delitem__(self, package_name):
        return self.__setitem__(package_name, False)

    # def setAutoCheckouts(self, checkouts_list):
    #     config = ConfigParser(interpolation=ExtendedInterpolation())
    #     with open(self.file_location) as f:
    #         config.readfp(f)
    #     checkouts = '\n'.join(checkouts_list)
    #     config.set('buildout', 'auto-checkout', checkouts)
    #     with open(self.file_location, 'w') as f:
    #         config.write(f)

    def add(self, package_name):
        # TODO: Handle test-fix-only as well
        return self.__setitem__(package_name, True)

    def remove(self, package_name):
        # Remove from checkouts.cfg
        return self.__delitem__(package_name)


class PloneCoreBuildout(object):
    PLONE_COREDEV_LOCATION = "git://github.com/plone/buildout.coredev.git"

    def __init__(self, core_version=None):
        self.core_version = core_version
        self.location = mkdtemp()
        self.repo = self._clone()
        self.sources = SourcesFile(self.location + '/sources.cfg')
        self.versions = VersionsFile(self.location + '/versions.cfg')
        self.checkouts = CheckoutsFile(self.location + '/checkouts.cfg')

    def _clone(self):
        logger.info("Cloning github repository %s, branch=%s"\
                        % (self.location, self.core_version))
        git.Repo.clone_from(self.PLONE_COREDEV_LOCATION,
                            self.location,
                            branch=self.core_version,
                            depth=1)
