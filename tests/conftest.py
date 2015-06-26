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

import pytest
import os
import random
import string

@pytest.fixture
def TEST_DIR():
    return os.getcwd()

@pytest.fixture
def REPO_NAME():
    return "the_repo"

@pytest.fixture
def TEST_REPO(TEST_DIR, REPO_NAME):
    return os.path.join(TEST_DIR, REPO_NAME)

@pytest.fixture
def id_generator():
    def generator(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))
    return generator

def username_and_password(id_generator):
    return id_generator(), id_generator()

