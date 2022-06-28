from re import A
from typing import List
import pandas as pd
from pathlib import Path
import logging
from Smartscope.lib.file_manipulations import locate_file_in_directories, get_file_and_process
from Smartscope.lib.image_manipulations import mrc_to_png, auto_contrast_sigma, fourier_crop
from Smartscope.lib.montage import Montage, Movie
from Smartscope.lib.logger import add_log_handlers
from Smartscope.lib.generic_position import parse_mdoc
import os
import time
import shlex
import subprocess

logger = logging.getLogger(__name__)


def get_CTFFIN4_data(path: Path) -> List[float]:
    with open(path, 'r') as f:
        lines = [[float(j) for j in i.split(' ')] for i in f.readlines() if '#' not in i]

        ctf = pd.DataFrame.from_records(lines, columns=['l', 'df1', 'df2', 'angast', 'phshift', 'cc', 'ctffit'], exclude=[
            'l', 'phshift'])

        return dict(defocus=(ctf.df1 + ctf.df2) / 2,
                    astig=ctf.df1 - ctf.df2,
                    angast=ctf.angast,
                    ctffit=ctf.ctffit)


def CTFfind(input_mrc: str, output_directory: str, pixel_size: float, voltage: int = 200, spherical_abberation: float = 2.7) -> None:
    extraparam = ''
    output_file = os.path.join(output_directory, 'ctf.mrc')

    p = subprocess.run([os.getenv('CTFFIND')],
                       input=f'{input_mrc}\n{output_file}\n{pixel_size}\n{voltage}\n{spherical_abberation}\n0.1\n512\n30\n10\n5000\n50000\n200\nno\nno\nno\nno\nno',
                       encoding='ascii', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    logger.debug(p.stdout)
    logger.debug(p.stderr)

    mrc_to_png(output_file)


def align_frames(frames: str, output_file: str, output_shifts: str, gain: str, mdoc: str, voltage: int):
    com = f'alignframes -input {frames} -output {output_file} -gain {gain} -rotation -1 -dfile {mdoc} -volt {voltage} -plottable {output_shifts}'
    logger.debug(com)
    p = subprocess.run(shlex.split(com), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug(p.stdout.decode('utf-8'))
    logger.debug(p.stderr.decode('utf-8'))


def process_hm_from_frames(name, frames_file_name, frames_directories: list, spherical_abberation: float = 2.7):
    movie = Movie(name=name)
    if not movie.directory.exists():
        logger.info(f'{movie.directory} does not exists')
        return movie
    if movie.check_metadata():
        logger.info(f'Movie {frames_file_name} already processed. Skipping')
        return movie
    logger.info(f'Processing {frames_file_name}')
    directory, frames_file = locate_file_in_directories(directory_list=frames_directories, file_name=frames_file_name)
    if directory is None:
        logger.info(f"Frames not found in {', '.join(frames_directories)}. Skipping.")
        return movie
    mdoc = Path(directory, f'{frames_file_name}.mdoc')
    if not mdoc.exists():
        logger.info(f'Mdoc file not found {mdoc}. Skipping.')
        return movie
    movie.metadata = parse_mdoc(mdocFile=mdoc, movie=True)
    if not movie.shifts.exists() or not movie.ctf.exists():
        align_frames(frames_file, output_file=movie.raw, output_shifts=movie.shifts, gain=Path(
            directory, movie.metadata.iloc[-1].GainReference), mdoc=mdoc, voltage=movie.metadata.Voltage.iloc[-1])
        if not movie.image_path.exists():
            movie.make_symlink()
        CTFfind(input_mrc=movie.image_path, output_directory=movie.name,
                voltage=movie.metadata.Voltage.iloc[-1], pixel_size=movie.pixel_size, spherical_abberation=spherical_abberation)
    movie.read_image()
    movie.export_as_png(normalization=auto_contrast_sigma, binning_method=fourier_crop)
    movie.save_metadata()

    return movie


def process_hm_from_average(raw, name, scope_path_directory, spherical_abberation: float = 2.7):
    montage = get_file_and_process(raw, name, directory=scope_path_directory)
    montage.export_as_png(normalization=auto_contrast_sigma, binning_method=fourier_crop)
    if not montage.ctf.exists():
        CTFfind(input_mrc=montage.image_path, output_directory=montage.name,
                voltage=montage.metadata.Voltage.iloc[-1], pixel_size=montage.pixel_size, spherical_abberation=spherical_abberation)
    return montage


def processing_worker_wrapper(logdir, queue, output_queue=None):
    logging.getLogger('Smartscope').handlers.pop()
    logger.debug(f'Log handlers:{logger.handlers}')
    add_log_handlers(directory=logdir, name='proc.out')
    logger.debug(f'Log handlers:{logger.handlers}')
    logger.debug(f'{queue},{output_queue}')
    try:
        while True:
            logger.info(f'Approximate processing queue size: {queue.qsize()}')
            item = queue.get()
            logger.info(f'Got item {item} from queue')
            if item == 'exit':
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
