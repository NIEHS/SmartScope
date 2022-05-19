import logging
import os
import json
from Smartscope.lib.file_manipulations import clean_source_dir, process_montage
from Smartscope.lib.export_optics import export_optics
from Smartscope.core.models import *
from Smartscope.lib.db_manipulations import group_holes_for_BIS, add_targets
from django.db import transaction
from Smartscope.lib.Finders.basic_finders import find_square_center
from Smartscope.lib.file_manipulations import process_montage
# from Smartscope.server.models import SquareModel, HoleModel, import_session
from Smartscope.core.autoscreen import autoscreen
from Smartscope.lib.config import *
import numpy as np

proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


def add_holes(id, targets):
    instance = SquareModel.objects.get(pk=id)
    montage, is_metadata = process_montage(instance, mag_level='square', working_dir=instance.grid_id.directory)
    montage.targets = np.array(targets) + np.array([0, instance.shape_y // instance.binning_factor])
    montage.target_class = 'LatticeTarget'
    montage.centroid = find_square_center(montage.montage)
    targets = montage.create_targets(starting_index=len(instance.targets))
    holes = add_targets(instance.grid_id, instance, targets, HoleModel, manual_addition=True)
    return holes


def add_single_targets(id, *args):
    mainlog.info(f'Adding {len(args)} targets to square {id}')
    targets = []
    for i in args:
        j = i.split(',')
        j = [float(k) for k in j]

        targets.append(j)
    mainlog.debug(targets)
    holes = add_holes(id=id, targets=targets)
    mainlog.debug([h.__dict__ for h in holes])


def check_pause(microscope_id: str):
    pause = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'.pause_{microscope_id}'))
    paused = os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}'))

    print(json.dumps(dict(pause=pause, paused=paused)))


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
    proclog.debug(f"{grid_id} {square_id}")
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
    # holes_for_grouping = [h for h in filtered_holes if h.quality in [None, '1', '2']]
    # holes_for_grouping = [h for h in filtered_holes if h.is_good(plugins=plugins) and not h.is_excluded(protocol, square.targets_prefix)]

    proclog.debug(f'\nAll Holes = {len(all_holes)}\nFiltered holes = {len(filtered_holes)}\nHoles for grouping = {len(holes_for_grouping)}')

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


# def manage(*args):
#     arguments = ["manage.py", *args]  # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Smartscope.settings.server')
#     mainlog.debug(arguments)
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
    mainlog.debug(f"Running: {command} {' '.join(args)}")
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
        mainlog.exception(e)
    except KeyboardInterrupt:
        mainlog.info('Stopping Smartscope')
