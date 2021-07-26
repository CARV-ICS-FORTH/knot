#!/usr/bin/env python

from setuptools import setup

setup(name='karvdash-client',
      version='1.3.1',
      description='Client to the Karvdash (Kubernetes CARV Dashboard) API',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      url='https://github.com/CARV-ICS-FORTH/karvdash',
      author='FORTH-ICS',
      license='Apache-2.0',
      packages=['karvdash_client'],
      entry_points={'console_scripts': ['karvdashctl = karvdash_client.cli:main']},
      install_requires=['requests>=2.23'],
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: Console',
                   'Programming Language :: Python :: 3.7',
                   'Operating System :: OS Independent',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'License :: OSI Approved :: Apache Software License'])
