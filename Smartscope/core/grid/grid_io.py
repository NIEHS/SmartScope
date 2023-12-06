import os
import time
import shutil
import sys
from typing import List, Union
from collections import namedtuple
from datetime import datetime
import glob
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

class GridIO:
    def create_dirs(settings):
        split_Workingdir = settings['Workingdir'].split('/')
        for d in [settings['Source'], os.path.join(settings['Source'], 'raw'), os.path.join(settings['Source'], 'reference'), '/'.join(split_Workingdir[:-2]), '/'.join(split_Workingdir[:-1]), settings['Workingdir']]:
            d = os.path.expanduser(d)
            if not os.path.isdir(d):
                os.mkdir(d)
                try:
                    os.chmod(d, 0o775)
                except PermissionError as err:
                    logger.warning(f'Could not set permissions on directory: {d}', err)


    def create_dirs_docker(working_dir):
        working_dir = os.path.join(os.getenv('AUTOSCREENDIR'), working_dir)
        split_Workingdir = working_dir.split('/')
        source = os.getenv('MOUNTLOC')
        for d in [source, os.path.join(source, 'raw'), os.path.join(source, 'reference'), '/'.join(split_Workingdir[:-1]), working_dir]:
            if not os.path.isdir(d):
                os.mkdir(d)
        return working_dir

    @staticmethod
    def create_grid_directories(path: str) -> None:
        path = Path(path)
        for directory in [path, path / 'raw', path / 'pngs']:
            directory.mkdir(exist_ok=True)