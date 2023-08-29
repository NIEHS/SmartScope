'''
packages required by all testing cases
'''
from ddt import ddt, data, unpack
import environ
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

env_file = os.path.join(DJANGO_DIR, 'core', 'settings', '.dev.env')
env = environ.Env()
environ.Env.read_env(env_file=env_file)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Smartscope.core.settings.server_docker')
# os.environ.setdefault('CONFIG', os.path.join(BUILD_DIR, "config/smartscope/"))
# os.environ.setdefault('EXTERNAL_PLUGINS_DIRECTORY',os.path.join(BUILD_DIR, 'external_plugins'))
# os.environ.setdefault('AUTOSCREENDIR',os.path.join(BUILD_DIR, 'data', 'smartscope'))
# os.environ.setdefault('AUTOSCREENSTORAGE',os.path.join(BUILD_DIR, 'data', 'smartscope'))
# os.environ.setdefault('TEMPDIR',os.path.join(BUILD_DIR, 'temp'))


def func_():
    return None