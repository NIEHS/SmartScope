import os
from pathlib import Path
import torch

from Smartscope.lib.preprocessing_methods import process_hm_from_frames


def is_gpu_enabled():
    print('GPU enabled:', torch.cuda.is_available())


def test_serialem_connection(ip: str, port: int):
    msg = 'Hello from smartscope'
    print(f'Testing connection to SerialEM by printing \"{msg}\" to the SerialEM log.')
    print(f'Using {ip}:{port}')
    import serialem as sem
    sem.ConnectToSEM(int(port), ip)
    sem.Echo(msg)
    sem.Exit(1)
    print('Finished, please look at the serialEM log for the message.')


def test_high_mag_frame_processing(test_dir=Path(os.getenv('AUTOSCREENDIR'), 'testing', 'montage_test'), name='test_frames'):
    os.chdir(test_dir)
    print(os.getcwd())
    frames_file_name = '20211119_AR2_0723-1_5383.tif'
    frames_dirs = [Path(os.getenv('AUTOSCREENDIR')), Path(os.getenv('TEST_FILES'), 'highmag_frames')]
    movie = process_hm_from_frames(name, frames_file_name=frames_file_name, frames_directories=frames_dirs)
    print(f'All movie data: {movie.check_metadata()}')
