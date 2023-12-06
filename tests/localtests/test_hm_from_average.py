
import os
import sys
build_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(build_dir)
SETTINGS_DIR = os.path.join(build_dir, 'SmartScope', 'Smartscope', 'core', 'settings')
import environ
env = environ.Env()
environ.Env.read_env(env_file=os.path.join(SETTINGS_DIR,'.dev.env'))
# print(os.getenv('CONFIG'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Smartscope.core.settings.server_docker')

from pathlib import Path
from typing import List, Tuple
import torch
import logging
import time

from SmartScope.Smartscope.lib.preprocessing_methods import process_hm_from_average

if __name__ == "__main__":
    '''
    test_dir = autoscreen_dir + group + session
    name = hole or highimage
    '''
    movie = process_hm_from_average(
        raw = "Htr1_1_square24_hole172.mrc",
        name = "Htr1_1_square24_hole172",
        scope_path_directory= "/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles/hole/raw",
        working_dir = '/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles/hole/'
    )
    print(f"All data: {movie}.")
