from setuptools import find_packages
from setuptools import setup


version = '2.0'

long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
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
          'PyGithub',
          'requests',
          'pyramid_mailer',
          'WebTest',
          'pytest',
          'pyramid_chameleon',
          'pyramid_debugtoolbar',
      ],
      entry_points="""\
      [paste.app_factory]
      main = mr.roboto:main
      """,
      )
