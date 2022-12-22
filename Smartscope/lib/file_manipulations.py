#!/usr/bin/env python


import os
import time
import shutil
import sys
import random
from typing import List, Union
from .montage import Montage
from collections import namedtuple
from datetime import datetime
import glob
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def split_path(path):
    Path = namedtuple('Path', ['path', 'root', 'file', 'name', 'ext'])
    path_split = path.split('/')
    root = '/'.join(path_split[:-1])
    file = path_split[-1]
    name, ext = '.'.join(file.split('.')[:-1]), file.split('.')[-1]
    splitted_path = Path(path, root, file, name, ext)
    logger.info(splitted_path)
    return splitted_path


def copy_file(file, remove=True):
    mdoc = file + '.mdoc'
    while not os.path.isfile(mdoc):
        logging.info('Waiting for ', mdoc)
        time.sleep(2)

    new_mdoc = shutil.copy2(mdoc, 'raw')

    new_file = shutil.copy2(file, 'raw')
    if all([os.path.getsize(mdoc) == os.path.getsize(new_mdoc),
            os.path.getsize(file) == os.path.getsize(new_file),
            remove is True]):
        exists = True
        while exists:
            try:
                os.remove(file)
                os.remove(mdoc)
                exists = False
            except OSError as err:
                logger.warning(err, 'Sleeping 2 secs and retrying')
                time.sleep(2)
    return split_path(new_file)


def get_file(file, remove=True):
    path = split_path(file)
    file_busy(path.file, path.root)
    return copy_file(path.path, remove=remove)


def file_busy(file, directory, timeout=1):
    count = 0
    logger.info(f'Waiting for {file}')
    sys.stdout.flush()
    while not os.path.isfile(os.path.join(directory, file)):
        time.sleep(timeout)
    else:
        logger.info("Montage still acquiring")
        sys.stdout.flush()
        while os.path.isfile(os.path.join(directory, '.lock')):
            time.sleep(timeout)
        else:
            logger.info('Montage acquisition finished, processing file.')


def now():
    return datetime.today().strftime('%Y-%m-%d %H:%M:%S')


def clean_source_dir(dir=os.getenv('MOUNTLOC')):
    files = glob.glob(os.path.join(dir, '*.txt'))
    files += glob.glob(os.path.join(dir, '.*'))

    logger.debug('\n'.join(files))
    [os.remove(file) for file in files if os.path.isfile(file)]
    open(os.path.join(dir, '.pause'), 'w').close()


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


def create_scope_dirs(scope_path):
    source = scope_path
    for d in [source, os.path.join(source, 'raw'), os.path.join(source, 'reference'), os.path.join(source, 'movies')]:
        if not os.path.isdir(d):
            os.mkdir(d)


def create_grid_directories(path: str) -> None:
    path = Path(path)
    for directory in [path, path / 'raw', path / 'pngs']:
        directory.mkdir(exist_ok=True)


def select_random_fake_file(funcname):
    TEST_FILES_ROOT = os.getenv('TEST_FILES')
    dirs = dict(atlas=os.path.join(TEST_FILES_ROOT, 'atlas'),
                square=os.path.join(TEST_FILES_ROOT, 'square'),
                lowmagHole=os.path.join(TEST_FILES_ROOT, 'hole'),
                highmag=os.path.join(TEST_FILES_ROOT, 'highmag'),
                highmagframes=os.path.join(TEST_FILES_ROOT, 'highmag_frames'),
                )
    dirname = dirs[funcname]
    return random.choice(glob.glob(f'{dirname}/*.???'))

def generate_fake_file(file, funcname, sleeptime=15, destination_dir=os.getenv('MOUNTLOC'), **kwargs):
    logger.info(f"Generating fake {file} from {funcname}")
    randomfile = select_random_fake_file(funcname)
    destination = os.path.join(destination_dir, file)
    shutil.copy(randomfile, destination)
    shutil.copy(f'{randomfile}.mdoc', f'{destination}.mdoc')
    while not all([os.path.getsize(randomfile) == os.path.getsize(destination),
                   os.path.getsize(f'{randomfile}.mdoc') == os.path.getsize(f'{destination}.mdoc')]):
        logger.debug(f'Fake files improperly copied, trying again')
        shutil.copy(randomfile, destination)
        shutil.copy(f'{randomfile}.mdoc', f'{destination}.mdoc')
    logger.info(f'Sleeping {sleeptime} sec to mimic scope acquisition')
    time.sleep(sleeptime)


def locate_file_in_directories(directory_list: List[str], file_name: str) -> Union[str, None]:
    """Locate a file from a list of possible locations and return the directory in which it was found or None if it couldn't be found"""
    for directory in directory_list:
        path = Path(directory, file_name)
        if path.exists():
            return directory, path
    return None, None


def get_file_and_process(raw, name, directory='', force_reprocess=False):
    if force_reprocess or not os.path.isfile(raw):
        path = os.path.join(directory, raw)
        get_file(path, remove=True)
    montage = Montage(name)
    montage.load_or_process(force_process=force_reprocess)
    return montage
