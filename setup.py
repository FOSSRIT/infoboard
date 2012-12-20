#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='infoboard',
    version='1.0',
    description='An app for tracking user contributions to Github organizations',
    author='Nathaniel Case',
    author_email='Qalthos@gmail.com',
    url='https://github.com/FOSSRIT/infoboard',
    packages=find_packages(),
    install_requires=['pygithub',
                      'knowledge',
                      'pyyaml',
                     ]
)
