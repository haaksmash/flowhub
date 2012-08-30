#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages
import os

setup(
    name="flowhub",
    version='0.2',
    description="Git-flow adapted for GitHub",
    author="Haak Saxberg",
    url="http://github.com/haaksmash/flowhub",
    packages=find_packages(),
    scripts=[
        os.path.join('bin', 'flowhub')
    ],
)
