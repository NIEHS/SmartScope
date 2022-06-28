import logging
import os
import json
from Smartscope.lib.file_manipulations import clean_source_dir  # , process_montage
from Smartscope.core.export_optics import export_optics
from Smartscope.core.models import *
from Smartscope.core.db_manipulations import group_holes_for_BIS, add_targets
from django.db import transaction
from Smartscope.lib.Finders.basic_finders import find_square_center
from Smartscope.core.autoscreen import autoscreen
from Smartscope.lib.config import *
from Smartscope.core.test_commands import is_gpu_enabled, test_serialem_connection
from Smartscope.core.utils.training_data import add_to_training_set
from Smartscope.core.preprocessing_pipelines import highmag_processing
import numpy as np


logger = logging.getLogger(__name__)


def add_holes(id, targets):
    instance = SquareModel.objects.get(pk=id)
    montage, is_metadata = process_montage(instance, mag_level='square', working_dir=instance.grid_id.directory)
    montage.targets = np.array(targets) + np.array([0, instance.shape_x])
    montage.target_class = 'LatticeTarget'
    montage.finder = 'Manual finder'
    montage.classifier = None
    montage.stage_z = instance.finders.all()[0].stage_z
    targets = montage.create_targets(starting_index=len(instance.targets))
    holes = add_targets(instance.grid_id, instance, targets, HoleModel)
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
    plugins = load_plugins()
    protocol = load_protocol(os.path.join(grid.directory, 'protocol.yaml'))
    logger.debug(f"{grid_id} {square_id}")
    collection_params = grid.params_id
    all_holes = list(HoleModel.objects.filter(square_id=square_id))
    excluded_groups = []
    for hole in all_holes:
        if hole.bis_type == 'center' and hole.status not in [None, 'queued']:
            print('Excluding group:', hole.bis_group)
            excluded_groups.append(hole.bis_group)

    filtered_holes = [h for h in all_holes if h.bis_group not in excluded_groups and h.status in [None, 'queued']]
    holes_for_grouping = []
    other_holes = []
    for h in filtered_holes:

        h.bis_group = None
        h.bis_type = None
        h.selected = False
        if h.is_good(plugins=plugins) and not h.is_excluded(protocol, square.targets_prefix)[0]:
            holes_for_grouping.append(h)
        else:
            other_holes.append(h)

    logger.debug(f'\nAll Holes = {len(all_holes)}\nFiltered holes = {len(filtered_holes)}\nHoles for grouping = {len(holes_for_grouping)}')

    holes = group_holes_for_BIS(holes_for_grouping, max_radius=collection_params.bis_max_distance,
                                min_group_size=collection_params.min_bis_group_size, queue_all=collection_params.holes_per_square == -1)

    with transaction.atomic():
        for hole in holes + other_holes:
            hole.save()


def continue_run(next_or_continue, microscope_id):
    if next_or_continue == "next":
        open(os.path.join(os.getenv('TEMPDIR'), f'next_{microscope_id}'), 'w').close()
    os.remove(os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}'))

    print(json.dumps({'continue': next_or_continue}))


def stop_session(sessionid):
    open(os.path.join(os.getenv('TEMPDIR'), f'{sessionid}.stop'), 'w').close()


# def manage(*args):
#     arguments = ["manage.py", *args]  # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Smartscope.settings.server')
#     logger.debug(arguments)
#     try:
#         from django.core.management import execute_from_command_line
#     except ImportError as exc:
#         raise ImportError(
#             "Couldn't import Django. Are you sure it's installed and "
#             "available on your PYTHONPATH environment variable? Did you "
#             "forget to activate a virtual environment?"
#         ) from exc
#     execute_from_command_line(arguments)


def run(command, *args):
    logger.debug(f"Running: {command} {' '.join(args)}")
    globals()[command](*args)


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
