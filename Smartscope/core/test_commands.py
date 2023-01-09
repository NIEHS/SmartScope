import os
from pathlib import Path
from typing import List, Tuple
import torch
from Smartscope.core.microscope_interfaces import TFSSerialemInterface
from Smartscope.lib.preprocessing_methods import process_hm_from_frames
from Smartscope.core.finders import find_targets
from Smartscope.core.models import Microscope
import logging
import time


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


def test_finder(plugin_name: str, raw_image_path: str, output_dir: str):  # output_dir='/mnt/data/testing/'
    from Smartscope.lib.montage import Montage
    from Smartscope.lib.image_manipulations import auto_contrast, save_image
    import cv2
    import math
    output_dir = Path(output_dir)
    try:
        output_dir.mkdir(exist_ok=True)
    except:
        logger.info(f'Could not create or find {str(output_dir)}')
    image = Path(raw_image_path)
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

# def test_grid_export(grid_id, export_to:str):
#     from Smartscope.core.models import AutoloaderGrid
#     from Smartscope.server.api.export_serializers import ExportMetaSerializer
#     from rest_framework_yaml.renderers import YAMLRenderer
    
#     serializer = ExportMetaSerializer(instance=AutoloaderGrid.objects.get(grid_id=grid_id))
#     with open(export_to,'wb') as file:
#         file.write(YAMLRenderer().render(data=serializer.data))

# def test_grid_import(file_to_import:str):
#     from Smartscope.server.api.export_serializers import ExportMetaSerializer
#     import yaml
#     with open(file_to_import,'r') as file:
#         data = yaml.safe_load(file) 
#     grid= ExportMetaSerializer(data=data)
#     grid.is_valid()
#     print(grid.errors) 
#     grid.save()

def test_protocol_command(microscope_id,detector_id,command):
    from Smartscope.core.models import Microscope, Detector
    import Smartscope.lib.Datatypes.microscope as micModels
    from Smartscope.core.settings.worker import PROTOCOL_COMMANDS_FACTORY
    microscope = Microscope.objects.get(pk=microscope_id)
    detector = Detector.objects.get(pk=detector_id)
    with TFSSerialemInterface(microscope = micModels.Microscope.from_orm(microscope),
                              detector= micModels.Detector.from_orm(detector),
                              atlasSettings= micModels.AtlasSettings.from_orm(detector)) as scope:
        PROTOCOL_COMMANDS_FACTORY[command](scope,None,None)


def list_plugins():
    from Smartscope.core.settings.worker import PLUGINS_FACTORY
    [print(f"{'#'*60}\n{name}:\n\n\t{plugin}\n{'#'*60}\n") for name,plugin in PLUGINS_FACTORY.items()]


def list_protocols():
    from Smartscope.core.settings.worker import PROTOCOLS_FACTORY
    [print(f"{'#'*60}\n{name}:\n\n\t{plugin}\n{'#'*60}\n") for name,plugin in PROTOCOLS_FACTORY.items()]


def acquire_fast_atlas_test(microscope_id):
    import serialem as sem
    from Smartscope.lib.microscope_methods import FastAtlas,make_serpent_pattern_in_mask

    microscope = Microscope.objects.get(pk=microscope_id)
    with TFSSerialemInterface(ip=microscope.serialem_IP,
                              port=microscope.serialem_PORT,
                              directory=microscope.windows_path,
                              scope_path=microscope.scope_path,
                              energyfilter=False,
                              loader_size=microscope.loader_size,
                              frames_directory='X:/testing/') as scope:
        scope.set_atlas_optics(62,100,5)
        sem.Search()
        sem.EarlyReturnNextShot(-1)
        X, Y, _, _, pixel_size, _ = sem.ImageProperties('A')
        logger.info(f'Setting atlas for {X}, {Y}, {pixel_size}')
        atlas = FastAtlas(atlas_imsize_x=X,atlas_imsize_y=Y,pixel_size_in_angst=pixel_size*10)
        atlas.generate_tile_mask(atlas_radius_in_um=990)
        atlas.make_stage_pattern(make_serpent_pattern_in_mask)
        sem.SetContinuous('R',1)
        sem.UseContinuousFrames(1)
        sem.StartFrameWaitTimer(-1)
        start_time = time.time()
        time_distances = []
        sem.MoveStageTo(*atlas.stage_movements[0][0])
        
        for ind, m in enumerate(atlas.stage_movements):
            start, end = m
            distance = abs(start[1]-end[1])
            exposure_time = 0.011 * distance + 4
            logger.info(f'Setting exposure time to {exposure_time:.1f}')
            sem.SetExposure('R', exposure_time)
            sem.MoveStageTo(*start)
            start_movement = time.time()
            logger.info(f'Starting movement {ind} at {start}, moving to {end}')
            sem.Echo(f'Movemement {ind}')
            sem.MoveStageTo(*end)
            movement_elapsed = time.time() - start_movement
            distance = abs(start[1]-end[1])
            logger.info(f'Movement {ind} took {movement_elapsed:.1f} for a distance of {distance}')
            time_distances.append([movement_elapsed,distance])

        sem.SetContinuous('R',0)
        elapsed = time.time() - start_time
        logger.info(f'Finished acquisition in {elapsed:.0f} seconds.')

def acquire_fast_atlas_test2(microscope_id,detector_id):
    from Smartscope.core.models import Microscope, Detector
    import Smartscope.lib.Datatypes.microscope as micModels
    import serialem as sem
    from Smartscope.lib.microscope_methods import FastAtlas,make_serpent_pattern_in_mask

    microscope = Microscope.objects.get(pk=microscope_id)
    detector = Detector.objects.get(pk=detector_id)
    with TFSSerialemInterface(microscope = micModels.Microscope.from_orm(microscope),
                              detector= micModels.Detector.from_orm(detector),
                              atlasSettings= micModels.AtlasSettings.from_orm(detector)) as scope:
        # scope.set_atlas_optics(62,100,5)
        sem.SetColumnOrGunValve(1)
        sem.Search()
        X, Y, _, _, pixel_size, _ = sem.ImageProperties('A')
        logger.info(f'Setting atlas for {X}, {Y}, {pixel_size}')
        atlas = FastAtlas(atlas_imsize_x=X,atlas_imsize_y=Y,pixel_size_in_angst=pixel_size*10)
        atlas.generate_tile_mask(atlas_radius_in_um=990)
        atlas.make_stage_pattern(make_serpent_pattern_in_mask)
        sem.SetContinuous('R',1)
        sem.UseContinuousFrames(1)
        sem.StartFrameWaitTimer(-1)
        start_time = time.time()
        time_distances = []
        sem.MoveStageTo(*atlas.stage_movements[0][0])
        
        for ind, m in enumerate(atlas.stage_movements):
            start, end = m
            distance = abs(start[1]-end[1])
            Path(scope.microscope.scopePath,'raw','atlas',str(ind)).mkdir(parents=True,exist_ok=True)
            sem.SetFolderForFrames(f'{scope.microscope.directory}raw/atlas/{ind}')
            sem.MoveStageTo(*start)
            sem.Record()
            start_movement = time.time()
            logger.info(f'Starting movement {ind} at {start}, moving to {end}')
            sem.Echo(f'Movemement {ind}')
            stage_movement = end - start
            sem.MoveStageWithSpeed(*stage_movement,0.5)
            sem.StopContinuous()
            movement_elapsed = time.time() - start_movement
            distance = abs(start[1]-end[1])
            logger.info(f'Movement {ind} took {movement_elapsed:.1f} for a distance of {distance}')
            time_distances.append([movement_elapsed,distance])

        sem.SetContinuous('R',0)
        elapsed = time.time() - start_time
        logger.info(f'Finished acquisition in {elapsed:.0f} seconds.')
