import os
from pathlib import Path
from typing import List, Tuple
import torch
from Smartscope.core.microscope_interfaces import GatanSerialemInterface
from Smartscope.lib.preprocessing_methods import process_hm_from_frames
import logging

logger = logging.getLogger(__name__)


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


def test_realign_to_square(microscope_id):
    from Smartscope.core.models import Microscope
    microscope = Microscope.objects.get(pk=microscope_id)
    with GatanSerialemInterface(ip=microscope.serialem_IP,
                                port=microscope.serialem_PORT,
                                directory=microscope.windows_path,
                                scope_path=microscope.scope_path,
                                energyfilter=False,
                                loader_size=microscope.loader_size) as scope:
        scope.realign_to_square()


def test_realign_to_hole(microscope_id):
    from Smartscope.core.models import Microscope
    microscope = Microscope.objects.get(pk=microscope_id)
    with GatanSerialemInterface(ip=microscope.serialem_IP,
                                port=microscope.serialem_PORT,
                                directory=microscope.windows_path,
                                scope_path=microscope.scope_path,
                                energyfilter=False,
                                loader_size=microscope.loader_size) as scope:
        scope.make_hole_ref(1.2)
        scope.align()


def refine_atlas_pixel_size(grids: List[str]):
    logger.info('Running atlas pixel size refinement')
    from Smartscope.core.models import AtlasModel
    grids = grids.split(',')
    instances = list(AtlasModel.objects.filter(grid_id__in=grids))
    grid_meshes = [instance.grid_id.meshSize.pitch for instance in instances]
    logger.debug(instances)
    average, std = refine_pixel_size_from_targets(instances, grid_meshes)
    error = abs(instances[0].pixel_size - average) / instances[0].pixel_size * 100
    logger.info(
        f'\n###################  Atlas magnification  ###################\nCalculated pixel size: {average:.1f} +/- {std:.1f} A/pix (n= {len(instances)}).\nThis is an difference of {error:.0f} % from the current {instances[0].pixel_size} A/pix value.\n#############################################################')


def refine_square_pixel_size(grids: List[str]):
    from Smartscope.core.models import SquareModel
    logger.info('Running square pixel size refinement')
    grids = grids.split(',')
    instances = list(SquareModel.objects.filter(grid_id__in=grids, status='completed'))
    grid_meshes = [instance.grid_id.holeType.pitch for instance in instances]
    logger.debug(instances)
    average, std = refine_pixel_size_from_targets(instances, grid_meshes)
    error = abs(instances[0].pixel_size - average) / instances[0].pixel_size * 100
    logger.info(
        f'\n###################  Square magnification ##################\nCalculated pixel size: {average:.1f} +/- {std:.1f} A/pix (n= {len(instances)}).\nThis difference of {error:.0f} % from the current {instances[0].pixel_size} A/pix value.\n############################################################')


def refine_pixel_size(grids: List[str]):
    logger.info('Running Atlas and Square level pixel size refinement.')
    refine_atlas_pixel_size(grids)
    refine_square_pixel_size(grids)


def refine_pixel_size_from_targets(instances, spacings) -> Tuple[float, float]:
    from Smartscope.core.models import Finder
    import numpy as np
    from scipy.spatial.distance import cdist
    pixel_sizes = []
    for instance, grid_mesh in zip(instances, spacings):
        targets = instance.base_target_query(manager='display').all().values_list('pk')
        coordinates = np.array(Finder.objects.filter(object_id__in=targets).values_list('x', 'y'))

        cd = cdist(coordinates, coordinates)
        cd.sort(axis=0)
        pixel_size = grid_mesh * 10000 / cd[1].mean()
        # logger.info(f'{instance} has a pixel size of {pixel_size:.2f} A/pix.')
        pixel_sizes.append(pixel_size)

    average = np.mean(pixel_sizes)
    std = np.std(pixel_sizes)
    return average, std


def list_plugins():
    from Smartscope.core.settings.worker import PLUGINS_FACTORY
    logger.info(f'Registered:\n{PLUGINS_FACTORY}')
