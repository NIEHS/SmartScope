import logging
import os
import sys
import json
from django.db import transaction
from django.conf import settings
from django.core.cache import cache

from Smartscope.core.models import *
from Smartscope.core.test_commands import *
from Smartscope.lib.image.montage import Montage
from Smartscope.lib.image.targets import Targets
from Smartscope.lib.image_manipulations import convert_centers_to_boxes
from Smartscope.core.db_manipulations import group_holes_for_BIS, add_targets
from .autoscreen import autoscreen
from .run_grid import run_grid
from .preprocessing_pipelines import highmag_processing

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


def add_holes(id, targets):
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
    start_number = instance.holemodel_set.order_by('-number')\
        .values_list('number', flat=True).first() + 1
    holes = add_targets(
        grid=instance.grid_id,
        parent=instance,
        targets=targets,
        model=HoleModel,
        finder=finder,
        start_number=start_number
    )
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


def regroup_bis(grid_id, square_id):
    grid = AutoloaderGrid.objects.get(grid_id=grid_id)
    square = SquareModel.objects.get(square_id=square_id)
    logger.debug(f"{grid_id} {square_id}")
    collection_params = grid.params_id
    logger.debug(f"Removing all holes from queue")
    HoleModel.objects.filter(square_id=square,status__isnull=True)\
        .update(selected=False,status=None,bis_group=None,bis_type=None)
    HoleModel.objects.filter(square_id=square,status='queued',)\
        .update(selected=False,status=None,bis_group=None,bis_type=None)
    filtered_holes = HoleModel.display.filter(square_id=square,status__isnull=True)
    holes_for_grouping = []
    other_holes = []
    for h in filtered_holes:
        if h.is_good() and not h.is_excluded()[0] and not h.is_out_of_range():
            holes_for_grouping.append(h)

    logger.info(f'Filtered holes = {len(filtered_holes)}\nHoles for grouping = {len(holes_for_grouping)}')

    holes = group_holes_for_BIS(
        holes_for_grouping,
        max_radius=collection_params.bis_max_distance,
        min_group_size=collection_params.min_bis_group_size,
        queue_all=collection_params.holes_per_square == 0
    )

    with transaction.atomic():
        for hole in sorted(holes, key=lambda x: x.selected):
            hole.save()
    
    logger.info('Regrouping BIS done.')


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

            