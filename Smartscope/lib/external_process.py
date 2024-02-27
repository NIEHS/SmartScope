'''
employ third-party software to process data
Note: all software should be installed
'''
from typing import List, Union
from pathlib import Path
import logging
import os
import sys
import shlex
import subprocess
from Smartscope.lib.image_manipulations import mrc_to_png

logger = logging.getLogger(__name__)



def align_frames(
        frames: str,
        output_file: Path,
        output_shifts: Path,
        gain: Union[str, None],
        mdoc: str,
        voltage: int
    ):
    '''
    software: alignframes in IMOD
    used by process_hm_from_frames()
    '''
    com = f'alignframes -mem 8 -input {frames} -output {output_file} -rotation -1 -pair -2'  + \
        f'-dfile {mdoc} -volt {voltage} -plottable {output_shifts}'
    if gain is not None:
       com += f' -gain {gain}'
    logger.debug(com)
    p = subprocess.run(shlex.split(com), \
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug(p.stdout.decode('utf-8'))
    logger.debug(p.stderr.decode('utf-8'))
    if all([output_file.exists(), output_shifts.exists()]):
        return True
    logger.debug(f"the output alignframes={output_file} or {output_shifts} doesn't exist.")
    return False

def CTFfind(
        input_mrc: str,
        output_directory: str,
        pixel_size: float,
        voltage: int = 200,
        spherical_abberation: float = 2.7
    ):
    '''
    software ctffind create CTF
    paramters:
    Pixel size                                   [1.0] : 0.8469
    Acceleration voltage                       [300.0] : 300
    Spherical aberration                         [2.7] : 2.7
    Amplitude contrast                          [0.07] : 0.1
    Size of power spectrum to compute            [512] : 512
    Minimum resolution                          [30.0] : 30
    Maximum resolution                           [5.0] : 10
    Minimum defocus                           [5000.0] : 5000
    Maximum defocus                          [50000.0] : 50000
    Defocus search step                        [500.0] : 200
    Expected (tolerated) astigmatism           [100.0] : 100
    Find additional phase shift?                  [no] : no
    '''
    extraparam = ''
    output_file = os.path.join(output_directory, 'ctf.mrc')
    # interactive mode required by ctffind
    inputs = [input_mrc, output_file, pixel_size, voltage, spherical_abberation,\
        0.1, 512, 30, 10, 5000, 50000, 200, 'no','no','no','no','no']
    inputs = '\n'.join([str(i) for i in inputs])
    # f'{input_mrc}\n{output_file}\n{pixel_size}\n{voltage}\n{spherical_abberation}\n0.1\n512\n30\n10\n5000\n50000\n200\nno\nno\nno\nno\nno',
    p = subprocess.run(
        [os.getenv('CTFFIND')],
        input=inputs,
        encoding='ascii', stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    logger.debug(p.stdout)
    logger.debug(p.stderr)
    if os.path.isfile(output_file):
        mrc_to_png(output_file)
        return output_file
    logger.debug(f"the output file CTF={output_file} doesn't exist.")
    return None
