
import os
import time
import shutil
import random
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

class Fake:
    
    @staticmethod
    def select_random_fake_file(funcname):
        TEST_FILES_ROOT = Path(os.getenv('TEST_FILES'))
        dirs = dict(atlas=TEST_FILES_ROOT / 'atlas',
                    square=TEST_FILES_ROOT / 'square',
                    lowmagHole=TEST_FILES_ROOT / 'hole',
                    highmag=TEST_FILES_ROOT / 'highmag',
                    highmagframes = TEST_FILES_ROOT / 'highmagframes',
                    )
        dirname = dirs[funcname]
        glob_pattern = '*.???'
        if funcname == 'highmagframes':
            glob_pattern = '*.tif'
        return random.choice(list(dirname.glob(glob_pattern)))
    
    @staticmethod
    def generate_fake_file(file, funcname, sleeptime=15, destination_dir=os.getenv('MOUNTLOC'), **kwargs):
        logger.info(f"Generating fake {file} from {funcname}")
        randomfile = Fake.select_random_fake_file(funcname)
        destination = os.path.join(destination_dir, file)
        if 'frames' in funcname:
            destination = os.path.join(destination_dir, randomfile.name)
            shutil.copy(list(randomfile.parent.glob('CountRef*'))[0], destination_dir)
        output_file = shutil.copy(randomfile, destination)
        shutil.copy(f'{randomfile}.mdoc', f'{destination}.mdoc')
        while not all([os.path.getsize(randomfile) == os.path.getsize(destination),
                    os.path.getsize(f'{randomfile}.mdoc') == os.path.getsize(f'{destination}.mdoc')]):
            logger.debug(f'Fake files improperly copied, trying again')
            output_file = shutil.copy(randomfile, destination)
            shutil.copy(f'{randomfile}.mdoc', f'{destination}.mdoc')
        logger.info(f'Sleeping {sleeptime} sec to mimic scope acquisition')
        time.sleep(sleeptime)
        return Path(output_file).name

