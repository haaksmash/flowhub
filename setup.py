#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages
import os

setup(
    name="flowhub",
    version='0.4.0',
    description="Git-flow adapted for GitHub",
    long_description=open("README.rst").read(),
    author="Haak Saxberg",
    url="http://github.com/haaksmash/flowhub",
    packages=find_packages(),
    scripts=[
        os.path.join('bin', 'flowhub')
    ],
    install_requires=[
        'GitPython == 0.3.2.RC1',
        'PyGithub == 1.4',
    ],
)
