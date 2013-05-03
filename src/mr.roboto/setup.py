from setuptools import setup, find_packages
import os

version = '1.0'

long_description = (
    open('README.txt').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.txt').read()
    + '\n' +
    open('CHANGES.txt').read()
    + '\n')

setup(name='mr.roboto',
      version=version,
      description="Plone Jenkins Middleware",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='',
      author='',
      author_email='',
      url='http://svn.plone.org/svn/collective/',
      license='gpl',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['mr'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'cornice',
          'configparser',
          'gitpython',
          'python-dateutil',
          'PyGithub',
          'persistent',
          'zope.schema',
          'requests',
          'lxml',
          'pyramid_mailer',
          'mongopersist',
          'WebTest',
          'pytest',
      ],
      entry_points="""\
      [paste.app_factory]
      main = mr.roboto:main
      """,
      )
