

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


def clean_source_dir(source_dir=None):
    if source_dir is None:
        source_dir = os.getenv('MOUNTLOC') 
    files = glob.glob(os.path.join(source_dir, '*.txt'))
    files += glob.glob(os.path.join(source_dir, '.*'))

    logger.debug('\n'.join(files))
    [os.remove(file) for file in files if os.path.isfile(file)]
    open(os.path.join(dir, '.pause'), 'w').close()


# TODO: depreciated in the future
def locate_file_in_directories(directory_list: List[str], file_name: str) -> Union[str, None]:
    """
    Locate a file from a list of possible locations
    and return the directory in which it was found
    or None if it couldn't be found
    """
    for directory in directory_list:
        path = Path(directory, file_name)
        if path.exists():
            return directory, path
    return None, None

