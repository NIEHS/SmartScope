#!/usr/bin/env python

from math import cos, radians
import os
import time
import shutil
import sys
import random

from cv2 import resize
from .montage import Atlas, Square, Hole, High_Mag, save_image
from collections import namedtuple
from datetime import datetime
import glob
import logging


proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


def split_path(path):
    Path = namedtuple('Path', ['path', 'root', 'file', 'name', 'ext'])
    path_split = path.split('/')
    root = '/'.join(path_split[:-1])
    file = path_split[-1]
    name, ext = '.'.join(file.split('.')[:-1]), file.split('.')[-1]
    splitted_path = Path(path, root, file, name, ext)
    proclog.info(splitted_path)
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
                proclog.warning(err, 'Sleeping 2 secs and retrying')
                time.sleep(2)
    return split_path(new_file)


def process_montage(obj, mag_level='atlas', save=True, raw_only=False, frames=False, force_reprocess=False, **kwargs):
    MAG_LEVELS = {'atlas': Atlas, 'square': Square, 'hole': Hole, 'high_mag': High_Mag}
    try:
        montage = MAG_LEVELS[mag_level.lower()](**obj.__dict__, **kwargs)
    except Exception as err:
        proclog.error(err)
    is_metadata = montage.create_dirs(force_reproces=force_reprocess)
    if not is_metadata:
        montage.parse_mdoc(file=obj.raw)
        montage.build_montage(raw_only=raw_only)
        save_image(montage.montage, montage._id, extension='png')
        if save:
            montage.save_metadata()
    return montage, is_metadata


def get_file(file, remove=True):
    path = split_path(file)
    file_busy(path.file, path.root)
    return copy_file(path.path, remove=remove)


def file_busy(file, directory, timeout=1):
    count = 0
    proclog.info(f'Waiting for {file}')
    sys.stdout.flush()
    while not os.path.isfile(os.path.join(directory, file)):
        time.sleep(timeout)
    else:
        proclog.info("Montage still acquiring")
        sys.stdout.flush()
        while os.path.isfile(os.path.join(directory, '.lock')):
            time.sleep(timeout)
        else:
            proclog.info('Montage acquisition finished, processing file.')


def now():
    return datetime.today().strftime('%Y-%m-%d %H:%M:%S')


def clean_source_dir(dir=os.getenv('MOUNTLOC')):
    files = glob.glob(os.path.join(dir, '*.txt'))
    files += glob.glob(os.path.join(dir, '.*'))

    proclog.debug('\n'.join(files))
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
                proclog.warning(f'Could not set permissions on directory: {d}', err)


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


def generate_fake_file(file, funcname, sleeptime=7, destination_dir=os.getenv('MOUNTLOC'), **kwargs):
    mainlog.info(f"Generating fake {file} from {funcname}")
    TEST_FILES_ROOT = os.getenv('TEST_FILES')
    dirs = dict(atlas=os.path.join(TEST_FILES_ROOT, 'atlas'),
                square=os.path.join(TEST_FILES_ROOT, 'square'),
                lowmagHole=os.path.join(TEST_FILES_ROOT, 'hole'),
                highmag=os.path.join(TEST_FILES_ROOT, 'highmag'),
                highmagframes=os.path.join(TEST_FILES_ROOT, 'highmag_frames'),
                )
    dirname = dirs[funcname]
    if 'frames' in kwargs.keys() and kwargs['frames']:
        dirname = dir[f'{funcname}_frames']

    randomfile = random.choice(glob.glob(f'{dirname}/*.???'))
    destination = os.path.join(destination_dir, file)
    shutil.copy(randomfile, destination)
    shutil.copy(f'{randomfile}.mdoc', f'{destination}.mdoc')
    while not all([os.path.getsize(randomfile) == os.path.getsize(destination),
                   os.path.getsize(f'{randomfile}.mdoc') == os.path.getsize(f'{destination}.mdoc')]):
        mainlog.debug(f'Fake files improperly copied, trying again')
        shutil.copy(randomfile, destination)
        shutil.copy(f'{randomfile}.mdoc', f'{destination}.mdoc')
    mainlog.info(f'Sleeping {sleeptime} sec to mimic scope acquisition')
    time.sleep(sleeptime)
