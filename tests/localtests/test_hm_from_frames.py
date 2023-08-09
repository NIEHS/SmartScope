
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
# from SmartScope.Smartscope.core.microscope_interfaces import TFSSerialemInterface
from Smartscope.lib.preprocessing_methods import process_hm_from_frames
# from SmartScope.Smartscope.core.finders import find_targets
# from SmartScope.Smartscope.core.models import Microscope

if __name__ == "__main__":
    '''
    test_dir = autoscreen_dir + group + session
    name = grid_id
    '''
    # test_dir=Path(os.getenv('AUTOSCREENDIR'), 'testing', 'montage_test')
    test_dir = '/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles'
    name='test_frames'
    # frames_file_name = '20211119_AR2_0723-1_5383.tif'
    frames_file_name = '20230321_AB_0317_2_1330_0.0.tif'
    # frames_dirs = [Path(os.getenv('AUTOSCREENDIR')), Path(os.getenv('TEST_FILES'), 'highmag_frames')]
    frames_dirs=[
        '/home/yuant2/nieh/build_smartscope/data/smartscope/',
        '/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles/highmag_frames'
    ]
    print('###frames_dirs: ', frames_dirs)
    movie = process_hm_from_frames(
        name,
        frames_file_name=frames_file_name,
        frames_directories=frames_dirs,
        working_dir = '/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles'
    )
    print(f'All movie data: {movie.check_metadata()}')