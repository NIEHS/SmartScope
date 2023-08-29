import logging
import os
import sys
import json
from django.db import transaction
from django.conf import settings

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
    targets = np.array(targets) + np.array([0, instance.shape_x])
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


def add_single_targets(id, *args):
    logger.info(f'Adding {len(args)} targets to square {id}')
    targets = []
    for i in args:
        j = i.split(',')
        j = [float(k) for k in j]

        targets.append(j)
    logger.debug(targets)
    holes = add_holes(id=id, targets=targets)

    logger.debug(holes)


def check_pause(microscope_id: str, session_id: str):
    pause = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'.pause_{microscope_id}'))
    paused = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}'))
    is_stop_file = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'{session_id}.stop'))

    print(json.dumps(dict(pause=pause, paused=paused, is_stop_file=is_stop_file)))


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

        # h.bis_group = None
        # h.bis_type = None
        if h.is_good() and not h.is_excluded()[0]:
            holes_for_grouping.append(h)
        # else:
        #     other_holes.append(h)

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



