# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


version = '2.0'

long_description = '{0}\n{1}\n{2}\n'.format(
    open('README.rst').read(),
    open('CONTRIBUTORS.rst').read(),
    open('CHANGES.rst').read(),
)

test_requires = [
    'pyramid_debugtoolbar',
    'pytest',
    'WebTest',
]

setup(
    name='mr.roboto',
    version=version,
    description='Plone Jenkins Middleware',
    long_description=long_description,
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Programming Language :: Python',
    ],
    keywords='',
    author='',
    author_email='',
    url='https://github.com/plone/mr.roboto',
    license='gpl',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['mr'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'configparser',
        'cornice',
        'gitpython',
        'PyGithub',
        'pyramid_chameleon',
        'pyramid_mailer',
        'requests',
        'setuptools',
    ],
    extras_require={
        'test': test_requires,
    },
    tests_require=test_requires,
    test_suite='mr.roboto.tests',
    entry_points="""
    [paste.app_factory]
    main = mr.roboto:main
    """,
)
