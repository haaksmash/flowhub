#!/usr/bin/env python
"""
Copyright (C) 2012 Haak Saxberg

This file is part of Flowhub, a command-line tool to enable various
Git-based workflows that interacts with GitHub.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

from distutils.core import setup
from setuptools import find_packages
import os

def get_readme():
    if os.path.isfile("README.txt"):
        filename = "README.txt"
    else:
        filename = "README.rst"
    with open(filename, 'r') as f:
        return f.read()

setup(
    name="flowhub",
    version='0.6.2',
    description="Git-flow adapted for GitHub",
    long_description=get_readme(),
    author="Haak Saxberg",
    author_email="haak.erling@gmail.com",
    url="http://github.com/haaksmash/flowhub",
    packages=find_packages(),
    scripts=[
        os.path.join('bin', 'flowhub')
    ],
    install_requires=[
        'GitPython == 0.3.6',
        'PyGithub > 1.25.1',
        'argcomplete >= 0.8.9',
    ],
)
