#!/usr/bin/env python

from setuptools import setup

setup(name='karvdash-client',
      version='1.2',
      description='Client to the karvdash (Kubernetes CARV Dashboard) API',
      url='https://www.ics.forth.gr/carv/',
      author='FORTH-ICS',
      license='Apache-2.0',
      packages=['karvdash_client'],
      entry_points={'console_scripts': ['karvdashctl = karvdash_client.cli:main']},
      install_requires=['requests>=2.23'],
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.6',
                   'Operating System :: OS Independent',
                   'Topic :: Software Development :: Libraries :: Python Modules'
                   'License :: OSI Approved :: Apache Software License'])
