
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
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    from build_smartscope.SmartScope.Smartscope.lib.image.movie import Movie
    from Smartscope.lib.preprocessing_methods import get_CTFFIN4_data
    
    name = 'HQFA_1_square155_hole36_0_hm'
    workding_dir = '/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles'
    movie = Movie(name=name, working_dir=workding_dir)
    print(movie.ctf)
    data = get_CTFFIN4_data(movie.ctf)
    print(data)