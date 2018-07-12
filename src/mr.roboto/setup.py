# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


version = '2.0'

readme_file = open('README.rst').read()
contributors_file = open('CONTRIBUTORS.rst').read()
changes_file = open('CHANGES.rst').read()
long_description = f'{readme_file}\n{contributors_file}\n{changes_file}\n'

test_requires = [
    'mock',
    'pyramid_debugtoolbar',
    'pytest',
    'WebTest',
    'testfixtures',
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
    author='Plone Foundation',
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
        'unidiff',
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
