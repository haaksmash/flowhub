#!/usr/bin/env python

from distutils.core import setup
import os

setup(
    name="Flowhub",
    version='0.2',
    description="Git-flow adapted for GitHub",
    author="Haak Saxberg",
    url="http://github.com/haaksmash/flowhub",
    packages=['flowhub'],
    scripts=[
        os.path.join('scripts','flowhub')
    ]
)
