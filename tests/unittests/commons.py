'''
packages required by all testing cases
'''
from ddt import ddt, data, unpack
import os
import numpy as np
from pathlib import Path
import sys
from unittest import TestCase, mock


TESTS_DIR = os.path.dirname(os.path.dirname(__file__))
TESTS_DATA_DIR = os.path.join(TESTS_DIR, 'data')
PROJECT_DIR = os.path.dirname(TESTS_DIR)
DJANGO_DIR = os.path.join(PROJECT_DIR, 'Smartscope')
sys.path.append(DJANGO_DIR)
sys.path.append(PROJECT_DIR)


def func_():
    return None