import os
import sys
from pathlib import Path
from typing import List, Tuple
import torch
import logging
import time
from django.conf import settings

from .interfaces.tfsserialem_interface import TFSSerialemInterface
from Smartscope.lib.preprocessing_methods import process_hm_from_frames
from .grid.finders import find_targets
from Smartscope.core.models import Microscope


logger = logging.getLogger(__name__)
# logger.info(settings)
# logger.info(settings.AUTOSCREENDIR)

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


def test_high_mag_frame_processing(
        test_dir=Path(settings.AUTOSCREENDIR, 'testing', 'montage_test'),
        name='test_frames'
    ):
    '''
    test_dir = autoscreen_dir + group + session
    name = grid_id
    '''
    os.chdir(test_dir)
    frames_file_name = '20230321_AB_0317_2_3302_0.0.tif'
    frames_dirs = [Path(os.getenv('AUTOSCREENDIR')), Path(os.getenv('TEST_FILES'), 'highmagframes')]
    movie = process_hm_from_frames(name, frames_file_name=frames_file_name, frames_directories=frames_dirs)
    print(f'All movie data: {movie.check_metadata()}')


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
        pixel_sizes.append(pixel_size)

    average = np.mean(pixel_sizes)
    std = np.std(pixel_sizes)
    return average, std


def test_finder(plugin_name: str, raw_image_path: str, output_dir: str, repeats=1):  # output_dir='/mnt/data/testing/'
    from Smartscope.lib.image.montage import Montage
    from Smartscope.lib.image_manipulations import auto_contrast, save_image
    import cv2
    import math

    
    output_dir = Path(output_dir)
    try:
        output_dir.mkdir(exist_ok=True)
    except:
        logger.info(f'Could not create or find {str(output_dir)}')
        
    image = Path(raw_image_path)
    iterations = []
    for ind in range(int(repeats)):
        start = time.time()
        logger.info(f'Testing finder {plugin_name} on image {raw_image_path}')
        logger.debug(f'{image.name}, {image.parent}')
        montage = Montage(image.stem, working_dir=output_dir)
        montage.raw = image
        montage.load_or_process()
        output, _ , _ , additional_outputs = find_targets(montage, [plugin_name])
        bit8_montage = auto_contrast(montage.image)
        bit8_color = cv2.cvtColor(bit8_montage, cv2.COLOR_GRAY2RGB)
        for i in output:
            cv2.circle(bit8_color, (i.x,i.y),20, (0, 0, 255), cv2.FILLED)
        if 'lattice_angle' in additional_outputs.keys():

            cv2.line(bit8_color,tuple(montage.center),(int(3000*math.sin(math.radians(additional_outputs['lattice_angle']))+montage.center[0]), int(3000*math.cos(math.radians(additional_outputs['lattice_angle'])))+ montage.center[1]),(0,255,0),10)
        logger.info(f"Saving diagnosis image in {Path(montage.directory,plugin_name.replace(' ', '_') + '.png')}")
        save_image(bit8_color, plugin_name, destination=montage.directory, resize_to=512)
        elapsed = time.time() - start
        iterations.append(f'{elapsed:.2f}')
        logger.info(f'Repeat {ind} took {elapsed} sec')
    logger.info(f"Time for each iterations {', '.join(iterations)}")

def test_protocol_command(microscope_id,detector_id,command, instance=None, instance_type=None, params=None):
    from Smartscope.core.models import Microscope, Detector, SquareModel
    from Smartscope.core.interfaces.microscope_methods import select_microscope_interface
    import Smartscope.core.interfaces.microscope as micModels
    from Smartscope.core.settings.worker import PROTOCOL_COMMANDS_FACTORY
    if instance_type=='square':
        logger.info(f'Selected square {instance}')
        instance = SquareModel.objects.get(pk=instance)
    microscope = Microscope.objects.get(pk=microscope_id)
    detector = Detector.objects.get(pk=detector_id)
    scopeInterface = select_microscope_interface(microscope)
    with scopeInterface(microscope = micModels.Microscope.model_validate(microscope),
                              detector= micModels.Detector.model_validate(detector),
                              atlas_settings= micModels.AtlasSettings.model_validate(detector)) as scope:
        PROTOCOL_COMMANDS_FACTORY[command](scope,params,instance)


def list_plugins():
    from Smartscope.core.settings.worker import PLUGINS_FACTORY
    [print(f"{'#'*60}\n{name}:\n\n\t{plugin}\n{'#'*60}\n") for name,plugin in PLUGINS_FACTORY.items()]


def list_protocols():
    from Smartscope.core.settings.worker import PROTOCOLS_FACTORY
    [print(f"{'#'*60}\n{name}:\n\n\t{plugin}\n{'#'*60}\n") for name,plugin in PROTOCOLS_FACTORY.items()]

def backup_db(ouput_directory='/mnt/backups/'):
    from datetime import datetime
    import subprocess
    filename = datetime.now().strftime("%Y%m%d_backup.sql")
    output_file = os.path.join(ouput_directory, filename)
    logger.info(f'Backing up database to {output_file}')
    command = f"mysqldump --user={os.getenv('MYSQL_USER')} --password={os.getenv('MYSQL_PASSWORD')} --host={os.getenv('MYSQL_HOST')} --port={os.getenv('MYSQL_PORT')} {os.getenv('MYSQL_DATABASE')} > {output_file}"
    subprocess.call(command, shell=True)
    logger.info('Finished backing up database.')

def restore_db(backup_file=None,backup_directory='/mnt/backups/'):
    from datetime import datetime
    import subprocess
    if backup_file is None:
        print('No backup file specified.')
        backup_files = sorted(Path(backup_directory).glob('*.sql'), reverse=True)
        print('\n'.join([f'\t{i+1}) {file.name}' for i,file in enumerate(backup_files)]))
        while True:
            in_value = input('Please select one from the list above: ')
            if in_value.isdigit() and 0 < int(in_value) <= len(backup_files):
                backup_file = backup_files[int(in_value)-1]
                break
    backup_file = os.path.join(backup_directory, backup_file)
    logger.info(f'Restoring database to {backup_file}')
    command = f"mysql --user={os.getenv('MYSQL_USER')} --password={os.getenv('MYSQL_PASSWORD')} --host={os.getenv('MYSQL_HOST')} --port={os.getenv('MYSQL_PORT')} {os.getenv('MYSQL_DATABASE')} < {backup_file}"
    subprocess.call(command, shell=True)
    logger.info('Finished restoring database.')

def test_find_hole_geometry(grid_id):
    from Smartscope.core.models import AutoloaderGrid
    from Smartscope.core.mesh_rotation import save_hole_geometry
    grid = AutoloaderGrid.objects.get(pk=grid_id)
    rotation, spacing = save_hole_geometry(grid)
    print(f'Updated grid {grid} with rotation: {rotation} degrees and spacing: {spacing} pixels.')