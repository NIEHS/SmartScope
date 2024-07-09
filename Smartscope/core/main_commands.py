import logging
import os
import json
from django.db import transaction
from django.core.cache import cache

from Smartscope.core.test_commands import *


import numpy as np


logger = logging.getLogger(__name__)

def main(args):
    """Main function for running the main SmartScope commands

    Args:
        args (list): list of command line argurments. First argument is the subcommand/program that should run followed by its specific arguments

    Example:
        Will launch the main Smarscope process

            $ python smartscope autoscreen grid_id: Will launch the main Smarscope process

    Todo:
        * Add a real parser

    """
    command = args.pop(0)
    try:
        run(command, *args)
    except Exception as e:
        logger.exception(e)
    except KeyboardInterrupt:
        logger.info('Stopping Smartscope')

def run(command, *args):
    logger.debug(f"Running command={command} {' '.join(args)}")
    globals()[command](*args)


def run_selectors(square_id):
    from Smartscope.core.models import SquareModel
    from Smartscope.core.selectors import selector_wrapper
    from Smartscope.lib.image.montage import Montage
    from Smartscope.core.protocols import get_or_set_protocol
    from django.core.cache import cache
    square = SquareModel.objects.get(pk=square_id)
    protocol = get_or_set_protocol(square.grid_id).square.targets
    montage = Montage(name=square.name, working_dir=square.grid_id.directory)
    montage.load_or_process()
    selector_wrapper(protocol.selectors, square, n_groups=5, montage=montage)
    cache_key = f'{square_id}_targets_methods'
    cache.delete(cache_key)


def add_holes(id, targets):
    from Smartscope.lib.image.montage import Montage
    from Smartscope.lib.image.targets import Targets
    from Smartscope.core.db_manipulations import add_targets
    from Smartscope.core.models import SquareModel, HoleModel
    from Smartscope.lib.image_manipulations import convert_centers_to_boxes
    
    instance = SquareModel.objects.get(pk=id)
    montage = Montage(name=instance.name, working_dir=instance.grid_id.directory)
    montage.load_or_process()
    targets = np.array(targets) 
    hole_size = holeSize if (holeSize := instance.grid_id.holeType.hole_size) is not None else 1.2
    targets = list(map(lambda t: convert_centers_to_boxes(
        t, montage.pixel_size, montage.shape_x, montage.shape_y, hole_size), targets))
    logger.debug(targets)
    finder = 'Manual finder'
    targets = Targets.create_targets_from_box(
        targets=targets,
        montage=montage,
        target_type='hole'
    )
    start_number = 1
    instance_number = instance.holemodel_set.order_by('-number')\
        .values_list('number', flat=True).first()
    if instance_number is not None:
        start_number += instance_number
    holes = add_targets(
        grid=instance.grid_id,
        parent=instance,
        targets=targets,
        model=HoleModel,
        finder=finder,
        start_number=start_number
    )

    run_selectors(id)
    return holes


def add_single_targets(id_, *args):
    logger.info(f'Adding {len(args)} targets to square {id_}')
    targets = []
    for i in args:
        j = i.split(',')
        j = [float(k) for k in j]

        targets.append(j)
    logger.debug(targets)
    holes = add_holes(id=id_, targets=targets)

    logger.debug(f'Successfully added {len(holes)} targets.')
    cache_key = f'{id_}_targets_methods'
    cache.delete(cache_key)


def check_pause(microscope_id: str, session_id: str):
    pause = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'.pause_{microscope_id}'))
    paused = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}'))
    is_stop_file = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'{session_id}.stop'))

    return dict(pause=pause, paused=paused, is_stop_file=is_stop_file)


def toggle_pause(microscope_id: str):
    pause_file = os.path.join(os.getenv('TEMPDIR'), f'.pause_{microscope_id}')
    if os.path.isfile(pause_file):
        os.remove(pause_file)
        print(json.dumps(dict(pause=False)))
    else:
        open(pause_file, 'w').close()
        print(json.dumps(dict(pause=True)))

def select_areas(mag_level, object_id, n_areas):
    from Smartscope.core.data_manipulations import select_n_areas
    from Smartscope.core.models import SquareModel, AtlasModel
    from Smartscope.core.db_manipulations import update
    if mag_level == 'atlas':
        obj = AtlasModel.objects.get(pk=object_id)
        is_bis = False
    else:
        obj = SquareModel.objects.get(pk=object_id)
        is_bis = obj.grid_id.params_id.bis_max_distance > 0
    output = select_n_areas(obj, int(n_areas), is_bis=is_bis)
    logger.info(f'Selected {output} areas.')
    with transaction.atomic():
        for obj in output:
            update(obj, selected=True, status='queued')
    print('Done.')

def regroup_bis(grid_id, square_id):
    from Smartscope.core.models import AutoloaderGrid, SquareModel, HoleModel
    from Smartscope.core.db_manipulations import group_holes_for_BIS
    from Smartscope.core.data_manipulations import filter_targets, apply_filter
    from Smartscope.core.status import status
    grid = AutoloaderGrid.objects.get(grid_id=grid_id)
    if square_id == 'all':
        queryparams = dict(grid_id=grid_id)
    else:
        queryparams = dict(grid_id=grid_id, square_id=square_id)
    logger.debug(f"{grid_id} {square_id}")
    collection_params = grid.params_id
    logger.debug(f"Removing all holes from queue")
    HoleModel.objects.filter(**queryparams,status__isnull=True)\
        .update(selected=False,status=status.NULL,bis_group=None,bis_type=None)
    HoleModel.objects.filter(**queryparams,status='queued',)\
        .update(selected=False,status=status.NULL,bis_group=None,bis_type=None)
    
    # filtered_holes = HoleModel.display.filter(**queryparams,status__isnull=True)
    holes_for_grouping = []
    # other_holes = []
    # for h in filtered_holes:
    #     if h.is_good() and not h.is_excluded()[0] and not h.is_out_of_range():
    #         holes_for_grouping.append(h)
    squares = SquareModel.display.filter(status=status.COMPLETED,**queryparams)
    for square in squares:
        logger.debug(f"Filtering square {square}, {square.pk}")
        targets = square.targets.filter(status__isnull=True)
        filtered = filter_targets(square, targets)
        holes_for_grouping += apply_filter(targets, filtered)


    logger.info(f'Holes for grouping = {len(holes_for_grouping)}')

    holes = group_holes_for_BIS(
        holes_for_grouping,
        max_radius=collection_params.bis_max_distance,
        min_group_size=collection_params.min_bis_group_size,
    )

    with transaction.atomic():
        for hole in holes:
            hole.save()
    
    logger.info('Regrouping BIS done.')
    return squares

def regroup_bis_and_select(grid_id, square_id):
    from Smartscope.core.models import AutoloaderGrid
    squares = regroup_bis(grid_id, square_id)
    grid = AutoloaderGrid.objects.get(grid_id=grid_id)
    for square in squares:
        select_areas('square', square.pk, grid.params_id.holes_per_square)


def continue_run(next_or_continue, microscope_id):
    if next_or_continue == "next":
        open(os.path.join(os.getenv('TEMPDIR'), f'next_{microscope_id}'), 'w').close()
    os.remove(os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}'))

    print(json.dumps({'continue': next_or_continue}))


def stop_session(sessionid):
    open(os.path.join(os.getenv('TEMPDIR'), f'{sessionid}.stop'), 'w').close()


def download_testfiles(overwrite=False):
    import subprocess as sub
    import shlex
    # archive_name = 'smartscope_testfiles.tar.gz'
    archive_name = 'SmartScopeInstallation.tar.gz'
    target_directory = '/mnt/testfiles/'
    archive_download_location = Path(target_directory,archive_name)
    print(archive_download_location)
    if overwrite == 'overwrite':
        print('Overwrite selected')
        command = f"rm -rf {' '.join(map(lambda x: str(x), list(Path(target_directory).iterdir())))}"
        print(command)
        p = sub.Popen(command)
        p.wait()
    
    is_directory_empty = any(Path(target_directory).iterdir())
    if is_directory_empty:
        print('It seems like the test files may already exist, use `download_testfiles overwrite` to force a full restart. Trying to see if process is complete')
    commands = [ f'wget https://docs.smartscope.org/downloads/{archive_name} -P {target_directory}',
                 f'tar -xvf {archive_download_location} --strip-components=1 -C {target_directory}', 
                 f'rm {archive_download_location}']
    if not archive_download_location.exists() and not is_directory_empty:
        print('Downloading the archive.')
        p = sub.Popen(shlex.split(commands[0]))
        p.wait()
    print(list(Path(target_directory).iterdir()))    
    if archive_download_location in list(Path(target_directory).iterdir()):
        print('Unpaking.')
        p = sub.Popen(shlex.split(commands[1]))
        p.wait()
    if archive_download_location.exists():
        print('Cleaning up.')
        p = sub.Popen(shlex.split(commands[2]))
        p.wait()
    print('Done.')

def get_atlas_to_search_offset(detector_name,maximum=0):
    from Smartscope.core.models import Detector, SquareModel
    if isinstance(maximum, str):
        maximum = int(maximum)
    detector = Detector.objects.filter(name__contains=detector_name).first()
    if detector is None:
        print(f'Could not find detector with name {detector_name}')
        return
    completed_square = SquareModel.just_labels.filter(status='completed',grid_id__session_id__detector_id__pk=detector.pk)
    count = completed_square.count()
    no_finder = 0
    total_done = 0
    if maximum > 0 and count > maximum:
        print(f'Found {count} completed squares, limiting to {maximum}')
        count=maximum
    else:
        print(f'Found {count} completed squares')
    
    for square in completed_square:
        if total_done == count:
            break
        finders = square.finders.all()
        recenter = finders.values_list('stage_x', 'stage_y').filter(method_name='Recentering').first()
        original = finders.values_list('stage_x', 'stage_y').filter(method_name='AI square finder').first()
        if any([recenter is None, original is None]):
            no_finder+=1
            total_done+=1
            print(f'Progress: {total_done/count*100:.0f}%, Skipped: {no_finder}', end='\r')
            continue
        diff = np.array(original) - np.array(recenter)
        if not 'array' in locals():
            array = diff.reshape(1,2)
            print(f'Progress: {total_done/count*100:.0f}%, Skipped: {no_finder}', end='\r')
            total_done+=1
            continue
        total_done+=1
        array = np.append(array, diff.reshape(1,2), axis=0)
        print(f'Progress: {total_done/count*100:.0f}%, Skipped: {no_finder}', end='\r')
    print(f'Progress: {total_done/count*100:.0f}%, Skipped: {no_finder}')
    mean = np.mean(array, axis=0).round(2)
    std = np.std(array, axis=0).round(2)
    print(f'Calculated offset from {total_done-no_finder} squares:\n\t X: {mean[0]} +/- {std[0]} um\n\t Y: {mean[1]} +/-  {std[1]} um \n')
    set_values = 'unset'
    while set_values not in ['y', 'n']:
        set_values = input(f'atlas_to_search_offset_x={mean[0]} um\natlas_to_search_offset_y={mean[1]} um\n\nSet values of for {detector}? (y/n)')
    if set_values == 'y':
        detector.atlas_to_search_offset_x = mean[0]
        detector.atlas_to_search_offset_y = mean[1]
        detector.save()
        print('Saved')
        return
    print('Skip setting values')


def export_grid(grid_id, export_to=''):
    from Smartscope.core.models import AutoloaderGrid
    from Smartscope.core.utils.export_import import export_grid
    grid = AutoloaderGrid.objects.get(grid_id=grid_id)
    if export_to == '':
        export_to = os.path.join(grid.directory, 'export.yaml')
        print(f'Export path not specified. Exporting to default loacation: {export_to}')
    export_grid(grid, export_to=export_to)
    print('Done.')

def import_grid(file:str, group:str='', user:str=''):
    from Smartscope.core.utils.export_import import import_grid
    if not Path(file).exists():
        print(f'File {file} does not exist.')
        return
    print(f'Importing {file} into the smartscope database.')
    import_grid(file, override_group=group, override_user=user)
    print('Done.')


def extend_lattice(square_id):
    from Smartscope.core.models import SquareModel
    from Smartscope.lib.Datatypes.grid_geometry import GridGeometry, GridGeometryLevel
    from Smartscope.core.mesh_rotation import calculate_hole_geometry
    from Smartscope.lib.Finders.lattice_extension import lattice_extension
    from Smartscope.lib.image.montage import Montage
    square = SquareModel.objects.get(pk=square_id)
    grid = square.grid_id
    geometry = GridGeometry.load(directory=grid.directory)
    rotation, spacing = geometry.get_geometry(level=GridGeometryLevel.SQUARE)
    if any([rotation is None, spacing is None]):
        rotation, spacing = calculate_hole_geometry(grid)
    montage = Montage(name=square.name, working_dir=grid.directory)
    montage.read_image()
    targets = square.holemodel_set.all()
    if targets.count() == 0:
        print('No targets found. The square needs at least one target to center the lattice on.')
        return
    coords = np.array([t.coords for t in targets])
    new_targets = lattice_extension(coords, montage.image, rotation, spacing)
    print(json.dumps(new_targets.tolist()))

def highmag_processing(grid_id: str, *args, **kwargs):
    from .preprocessing_pipelines import highmag_processing
    highmag_processing(grid_id, *args, **kwargs)

def autoscreen(session_id:str):
    from .autoscreen import autoscreen
    autoscreen(session_id=session_id)

def reload_plugins():
    from Smartscope.core.settings.worker import PLUGINS_FACTORY
    PLUGINS_FACTORY.reload_plugins()

def list_plugins():
    from Smartscope.core.settings.worker import PLUGINS_FACTORY
    plugins = PLUGINS_FACTORY.get_plugins()
    print(plugins)
    return plugins
    

            