from typing import List, Union
import pandas as pd
from pathlib import Path
import logging
import os
import sys
import time
import shlex
import subprocess

from .image.image_file import parse_mdoc
from .image.movie import Movie
from .image.montage import Montage
from .file_manipulations.file_manipulations import split_path, file_busy, copy_file
from .image_manipulations import mrc_to_png, auto_contrast_sigma, fourier_crop, export_as_png


from .external_process import align_frames, CTFfind
from Smartscope.lib.logger import add_log_handlers


logger = logging.getLogger(__name__)


'''
TODO: deprecated in the future
def get_CTFFIN4_data(ctf_text: Path) -> List[float]:
    with open(ctf_text, 'r') as f:
        lines = [[float(j) for j in i.split(' ')] \
            for i in f.readlines() if '#' not in i]
        ctf = pd.DataFrame.from_records(lines,
            columns=['l', 'df1', 'df2', 'angast', 'phshift', 'cc', 'ctffit'],
            exclude=['l', 'phshift']).iloc[0]

    return {
        'defocus': (ctf.df1 + ctf.df2) / 2,
        'astig': ctf.df1 - ctf.df2,
        'angast': ctf.angast,
        'ctffit': ctf.ctffit,
    }
'''


def get_CTFFIND5_data(ctf_text: Path) -> List[float]:
    '''
    get results from ctf_*.txt determined by ctffinder
    args: 
    '''
    logger.info(f"Try to read CTF file {ctf_text}")
    ctf={}
    columns=['l', 'df1', 'df2', 'angast', 'phshift', 'cc', 'ctffit','tilt_axis_angle','tilt_angle','ice_thickness']
    with open(ctf_text, 'r') as f:
        for line in f:
            if not line.startswith('#'):
                values = line.rstrip().split()
                for k,v in zip(columns, values):
                    ctf[k] = float(v)
                break
    return {
        'defocus': (ctf['df1'] + ctf['df2']) / 2,
        'astig': ctf['df1'] - ctf['df2'],
        'angast': ctf['angast'],
        'ctffit': ctf['ctffit'],
        'tilt_axis_angle': ctf['tilt_axis_angle'],
        'tilt_angle': ctf['tilt_angle'],
        'ice_thickness': int(round(ctf['ice_thickness']/10))
    }

def process_hm_from_frames(
        name: str,
        frames_file_name: str,
        frames_directories: list,
        spherical_abberation: float = 2.7,
        working_dir = None
    ):
    '''
    process high-resolution image from *.tif
    employ third-party software: alignframes and ctffind
    commandS: highmag_processsing <grid_id>
    used by core.processing_pipelines.queue_incomplete_processes
    '''
    movie = Movie(name=name, working_dir=working_dir)
    movie.validate_working_dir()
    if not movie.has_directory():
        return movie
    if movie.metadata_exist():
        return movie

    # validate frames file (*.tif)
    has_frames = movie.check_frames(
        frames_directories, frames_file_name
    )
    if not has_frames:
        return movie
    
    # validate *.mdoc file
    mdoc_file = movie.check_mdoc(frames_file_name)
    if mdoc_file is None:
        return movie
    time.sleep(10)

    if not movie.shifts.exists() or not movie.image_path.exists():
        try:
            gain = Path(movie.frames_directory, movie.metadata.GainReference.iloc[-1])
        except AttributeError:
            gain = None

        # launch alignframes
        logger.info(f"Aligning frames for {movie.name}")
        has_aligned = align_frames(
            frames=movie.frames_file,
            output_file=movie.image_path,
            output_shifts=movie.shifts,
            gain=gain,
            mdoc=mdoc_file,
            voltage=movie.metadata.Voltage.iloc[-1]
        )
        if not has_aligned:
            return movie
        logger.info(f"Done aligning frames for {movie.name}")
        # if not movie.image_path.exists():
        #     movie.make_symlink()
    if not movie.ctf.exists():
        logger.info(f"Running CTFfind for {movie.name}")
        # launch ctffind
        ctf_file = CTFfind(
            input_mrc=movie.image_path,
            output_directory=movie.name,
            voltage=movie.metadata.Voltage.iloc[-1],
            pixel_size=movie.pixel_size,
            spherical_abberation=spherical_abberation
        )
        if not ctf_file:
            return movie
        logger.info(f"Done running CTFfind for {movie.name}")
    
    # create png based on mrc
    # mrc_to_png(ctf_file)
    movie.read_image()
    movie.set_shape_from_image()
    export_as_png(
        movie.image,
        movie.png,
        normalization=auto_contrast_sigma,
        binning_method=fourier_crop
    )
    movie.save_metadata()

    return movie


def process_hm_from_average(
        raw,
        name,
        scope_path_directory,
        spherical_abberation: float = 2.7,
        force_reprocess=False,
        remove=True,
        check_AWS = False,
        working_dir: str = ''
    ):
    '''
    process high-resolution images on average
    used by core.processing_pipelines.queue_incomplete_processes
    '''
    if force_reprocess or not os.path.isfile(raw):
        raw_file = os.path.join(scope_path_directory, raw)
        path = split_path(raw_file)
        file_busy(path.file, path.root)
        copy_file(path.path, remove=remove)

    # process montage
    montage = Montage(name=name, working_dir=working_dir)
    if force_reprocess or not montage.check_metadata(check_AWS=check_AWS):
        montage.metadata = parse_mdoc(montage.mdoc, montage.is_movie)
        montage.build_montage()
        montage.read_image()
        montage.save_metadata()

    print(f"###montage.image{montage.image}, montage.png={montage.png}, mdoc={montage.raw}")
    export_as_png(
        montage.image,
        montage.png,
        normalization=auto_contrast_sigma,
        binning_method=fourier_crop
    )

    # calculate CTF
    if not montage.ctf.exists():
        CTFfind(
            input_mrc=montage.image_path,
            output_directory=montage.name,
            voltage=montage.metadata.Voltage.iloc[-1],
            pixel_size=montage.pixel_size,
            spherical_abberation=spherical_abberation
        )
    return montage

def clear_queue(queue):
    logger.info(f'Clearing queue')
    queue.task_done()
    while not queue.empty():
        item = queue.get()
        logger.info(f'Got item={item} from queue')
        queue.task_done()

def processing_worker_wrapper(logdir, queue, output_queue=None):
    logger.info(f"processing worker: {logdir}\t{queue}\t{output_queue}")
    logging.getLogger('Smartscope').handlers.pop()
    logger.debug(f'Log handlers:{logger.handlers}')
    add_log_handlers(directory=logdir, name='proc.out')
    logger.debug(f'Log handlers:{logger.handlers}')
    logger.debug(f'{queue},{output_queue}')
    try:
        while True:
            logger.info(f'Approximate processing queue size: {queue.qsize()}')
            item = queue.get()
            logger.info(f'Got item={item} from queue')
            if item == 'exit':
                logger.info('Breaking processing worker loop.')
                clear_queue(queue)
                break
            if item is not None:
                logger.debug(f'Running {item[0]} {item[1]} {item[2]} from queue')
                output = item[0](*item[1], **item[2])
                queue.task_done()
                if output_queue is not None and output is not None:
                    logger.debug(f'Adding {output} to output queue')
                    output_queue.put(output)
            else:
                logger.debug(f'Sleeping 2 sec')
                time.sleep(2)
    except Exception as e:
        logger.error("Error in the processing worker")
        logger.exception(e)
        clear_queue(queue)
    except KeyboardInterrupt as e:
        logger.info('SIGINT recieved by the processing worker')
        clear_queue(queue)

