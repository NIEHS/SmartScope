from typing import List, Union
import pandas as pd
from pathlib import Path
import logging
import os
import sys
import time
import shlex
import subprocess

from Smartscope.lib.file_manipulations import get_file_and_process
from Smartscope.lib.image_manipulations import mrc_to_png, auto_contrast_sigma, fourier_crop, export_as_png
from Smartscope.lib.montage import Montage
from .movie import Movie
from .external_process import align_frames, CTFfind
from Smartscope.lib.logger import add_log_handlers


logger = logging.getLogger(__name__)


def get_CTFFIN4_data(path: Path) -> List[float]:
    with open(path, 'r') as f:
        lines = [[float(j) for j in i.split(' ')] for i in f.readlines() if '#' not in i]

        ctf = pd.DataFrame.from_records(lines, columns=['l', 'df1', 'df2', 'angast', 'phshift', 'cc', 'ctffit'], exclude=[
            'l', 'phshift']).iloc[0]

    return dict(defocus=(ctf.df1 + ctf.df2) / 2,
                astig=ctf.df1 - ctf.df2,
                angast=ctf.angast,
                ctffit=ctf.ctffit)

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
    if not mdoc_file:
        return movie
    time.sleep(10)

    if not movie.shifts.exists() or not movie.ctf.exists():
        try:
            gain = Path(movie.frames_directory, movie.metadata.GainReference.iloc[-1])
        except AttributeError:
            gain = None

        # launch alignframes
        has_aligned = align_frames(
            frames=movie.frames_file,
            output_file=movie.raw,
            output_shifts=movie.shifts,
            gain=gain,
            mdoc=mdoc_file,
            voltage=movie.metadata.Voltage.iloc[-1]
        )
        if not has_aligned:
            return movie
        if not movie.image_path.exists():
            movie.make_symlink()
        
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
    # create png based on mrc
    mrc_to_png(ctf_file)
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


def process_hm_from_average(raw, name, scope_path_directory, spherical_abberation: float = 2.7):
    montage = get_file_and_process(raw, name, directory=scope_path_directory)
    export_as_png(montage.image, montage.png, normalization=auto_contrast_sigma, binning_method=fourier_crop)
    if not montage.ctf.exists():
        CTFfind(input_mrc=montage.image_path, output_directory=montage.name,
                voltage=montage.metadata.Voltage.iloc[-1], pixel_size=montage.pixel_size, spherical_abberation=spherical_abberation)
    return montage


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
                queue.task_done()
                logger.info('Breaking processing worker loop.')
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
    except KeyboardInterrupt as e:
        logger.info('SIGINT recieved by the processing worker')
