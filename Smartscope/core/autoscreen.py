
import os
from random import random
import sys
import time
import shlex
from typing import Union
from Smartscope.core.microscope_interfaces import FakeScopeInterface, SerialemInterface
from Smartscope.core.selectors import selector_wrapper
from Smartscope.core.models import AutoloaderGrid, ScreeningSession, HoleModel, SquareModel, Process
from Smartscope.lib.image_manipulations import auto_contrast, auto_contrast_sigma, fourier_crop
from Smartscope.lib.montage import Montage, Movie, create_targets, find_targets
from Smartscope.lib.preprocessing_methods import processing_worker_wrapper
from Smartscope.lib.file_manipulations import get_file_and_process, create_grid_directories
from Smartscope.core.db_manipulations import update, select_n_areas, queue_atlas, add_targets, group_holes_for_BIS, add_high_mag
from Smartscope.lib.config import load_plugins, save_protocol, load_default_protocol, load_protocol
from Smartscope.lib.logger import add_log_handlers
from django.db import transaction
from django.utils import timezone
from math import cos, radians
import multiprocessing
import logging
import subprocess


logger = logging.getLogger(__name__)


def get_queue(grid):
    """Query database to refresh the queue

    Args:
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models

    Returns:
        (list): [squares,holes]; List of SquareModels that are status='queued' and List of HoleModels that are status='queued'
    """
    squares = list(grid.squaremodel_set.filter(selected=1, status__in=['queued', 'started']).order_by('number'))
    holes = list(grid.holemodel_set.filter(selected=1, square_id__status='completed', status__in=['queued', 'started', 'processed',
                                                                                                  'acquired']).order_by('square_id__completion_time', 'number'))
    return squares, [h for h in holes if not h.bisgroup_acquired]


def resume_incomplete_processes(queue, grid, microscope_id):
    """Query database for models with incomplete processes and adds them to the processing queue

    Args:
        queue (multiprocessing.JoinableQueue): multiprocessing queue of objects for processing by    the processing_worker
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models
        session (ScreeningSession): ScreeningSession object from Smartscope.server.models
    """
    squares = grid.squaremodel_set.filter(selected=1).exclude(
        status__in=['queued', 'started', 'completed']).order_by('number')
    holes = grid.holemodel_set.filter(selected=1).exclude(
        status__in=['queued', 'started', 'processed', 'completed']).order_by('square_id__number', 'number')
    for square in squares:
        logger.info(f'Square {square} was not fully processed')
        transaction.on_commit(lambda: queue.put([process_square_image, [square, grid, microscope_id], {}]))
    for hole in holes:
        logger.info(f'Hole {hole} was not fully processed')
        transaction.on_commit(lambda: queue.put([process_hole_image, [hole, microscope_id], {}]))


def print_queue(squares, holes, session):
    """Prints Queue to a file for displaying to the frontend

    Args:
        squares (list): list of squares returned from the get_queue method
        holes (list): list of holes returned from the get_queue method
        session (ScreeningSession): ScreeningSession object from Smartscope.server.models
    """
    string = ['------------------------------------------------------------\nCURRENT QUEUE:\n------------------------------------------------------------\nSquares:\n']
    for s in squares:
        string.append(f"\t{s.number} -> {s.name}\n")
    string.append(f'------------------------------------------------------------\nHoles: (total={len(holes)})\n')
    for h in holes:
        string.append(f"\t{h.number} -> {h.name}\n")
    string.append('------------------------------------------------------------\n')
    string = ''.join(string)
    with open(os.path.join(session.directory, 'queue.txt'), 'w') as f:
        f.write(string)


def load_protocol_wrapper(protocol):
    protocol_file = 'protocol.yaml'
    if not os.path.isfile(protocol_file):
        return load_default_protocol(protocol)
    return load_protocol()


def is_stop_file(sessionid: str) -> bool:
    stop_file = os.path.join(os.getenv('TEMPDIR'), f'{sessionid}.stop')
    if os.path.isfile(stop_file):
        logger.debug(f'Stop file {stop_file} found.')
        os.remove(stop_file)
        raise KeyboardInterrupt()


def add_IS_offset(hole_size_in_um: float, mesh_type: str, offset_in_um: float = -1) -> float:
    if offset_in_um != -1:
        return offset_in_um
    hole_radius = hole_size_in_um / 2
    max_offset_factor = 0.5
    if mesh_type == 'Carbon':
        max_offset_factor = 0.8
    offset_in_um = round(random() * hole_radius * max_offset_factor, 1)
    logger.info(f'Adding a {offset_in_um} \u03BCm offset to sample ice gradient along the hole.')
    return offset_in_um


def run_grid(grid, session, processing_queue, scope):
    """Main logic for the SmartScope process

    Args:
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models
        session (ScreeningSession): ScreeningSession object from Smartscope.server.models
    """

    if grid.status == 'complete':
        logger.info(f'{grid.name} already complete')
        return
    session_id = session.pk
    microscope = session.microscope_id

    # Set the Websocket_update_decorator grid property
    # processing_queue.put(['set_update', [grid]])
    update.grid = grid

    logger.info(f'Starting {grid.name}')  # \nHoleType: {grid.holeType.name}

    grid = update(grid, refresh_from_db=True, last_update=None)

    if grid.status is None:
        grid = update(grid, status='started', start_time=timezone.now())

    create_grid_directories(grid.directory)
    os.chdir(grid.directory)
    processing_queue.put([os.chdir, [grid.directory], {}])
    params = grid.params_id
    # ADD the new protocol loader
    protocol = load_protocol_wrapper(grid.protocol)
    save_protocol(protocol)

    resume_incomplete_processes(processing_queue, grid, session.microscope_id)
    subprocess.Popen(shlex.split(f'smartscope.py highmag_processing smartscopePipeline {grid.grid_id} 1'))
    is_stop_file(session_id)
    atlas = queue_atlas(grid)

    scope.loadGrid(grid.position)
    is_stop_file(session_id)
    scope.setup(params.save_frames, params.zeroloss_delay)
    grid_type = grid.holeType
    grid_mesh = grid.meshMaterial
    if atlas.status == 'queued' or atlas.status == 'started':
        atlas = update(atlas, status='started')
        print('Waiting on atlas file')
        path = os.path.join(microscope.scope_path, atlas.raw)
        scope.atlas(mag=session.detector_id.atlas_mag, c2=session.detector_id.c2_perc, spotsize=session.detector_id.spot_size,
                    tileX=params.atlas_x, tileY=params.atlas_y, file=atlas.raw)
        atlas = update(atlas, status='acquired')

    if atlas.status == 'acquired':
        logger.info('Atlas acquired')
        montage = get_file_and_process(raw=atlas.raw, name=atlas.name, directory=microscope.scope_path)
        montage.export_as_png()
        targets, finder_method, classifier_method = find_targets(montage, load_protocol()['squareFinders'])
        targets = create_targets(targets, montage, target_type='square')
        squares = add_targets(grid, atlas, targets, SquareModel, finder_method, classifier_method)
        atlas = update(atlas, status='processed', pixel_size=montage.pixel_size,
                       shape_x=montage.shape_x, shape_y=montage.shape_y, stage_z=montage.stage_z)
    if atlas.status == 'processed':
        selector_wrapper(protocol[f'{atlas.targets_prefix}Selectors'], atlas, n_groups=5)
        select_n_areas(atlas, grid.params_id.squares_num)
        atlas = update(atlas, status='completed')

    logger.info('Atlas analysis is complete')

    running = True
    restarting = True
    is_done = False
    while running:
        is_stop_file(session_id)
        grid = update(grid, refresh_from_db=True, last_update=None)
        params = grid.params_id
        is_bis = params.bis_max_distance > 0
        if grid.status == 'aborting':
            break
        else:
            squares, holes = get_queue(grid)
        print_queue(squares, holes, session)
        if len(holes) > 0 and (len(squares) == 0 or grid.collection_mode == 'screening'):
            is_done = False
            hole = holes[0]
            finder = hole.finders.first()
            stage_x, stage_y, stage_z = finder.stage_x, finder.stage_y, finder.stage_z
            if is_bis and hole.bis_group is not None:
                bis_holes = list(grid.holemodel_set(manager='display')
                                 .filter(bis_group=hole.bis_group, bis_type='is_area')
                                 .exclude(status__in=['acquired', 'completed'])
                                 .order_by('number'))
                bis_holes += [hole]
            else:
                bis_holes = [hole]

            if hole.status == 'queued' or hole.status == 'started':
                restarting = False
                hole = update(hole, status='started')

                scope.lowmagHole(stage_x, stage_y, stage_z, round(params.tilt_angle, 1),
                                 file=hole.raw, is_negativestain=grid.holeType.name in ['NegativeStain', 'Lacey'])
                scope.focusDrift(params.target_defocus_min, params.target_defocus_max, params.step_defocus, params.drift_crit)
                hole = update(hole, status='acquired', completion_time=timezone.now())
                process_hole_image(hole, microscope)
                # transaction.on_commit(lambda: processing_queue.put([process_hole_image, [hole, microscope], {}]))
            if hole.status in ['acquired', 'processed']:
                if restarting:
                    restarting = False
                    logger.info(f'Restarting run, recentering on {hole} area before taking high-mag images')
                    scope.lowmagHole(stage_x, stage_y, stage_z, round(params.tilt_angle, 1),
                                     file=hole.raw, is_negativestain=grid.holeType.name in ['NegativeStain', 'Lacey'])
                    scope.focusDrift(params.target_defocus_min, params.target_defocus_max,
                                     params.step_defocus, params.drift_crit)

                logger.debug(f'{hole} is {hole.status} {bis_holes}')
                scope.reset_image_shift_values()
                for h in bis_holes:
                    hm, created = add_high_mag(grid, h)
                    logger.debug(f'Just created:{created} {hm}, {hm.pk}')
                    if hm.status in [None, 'started']:
                        finder = list(h.finders.all())[0]
                        offset = 0
                        if grid.collection_mode == 'screening' or params.offset_distance != -1:
                            offset = add_IS_offset(grid_type.hole_size, grid_mesh.name, offset_in_um=params.offset_distance)
                        isX, isY = stage_x - finder.stage_x + offset, (stage_y - finder.stage_y) * cos(radians(round(params.tilt_angle, 1)))
                        frames = scope.highmag(isX, isY, round(params.tilt_angle, 1), file=hm.raw, frames=params.save_frames)
                        hm = update(hm, is_x=isX, is_y=isY, offset=offset, frames=frames, status='acquired', completion_time=timezone.now())
                        if h != hole:
                            update(h, status='acquired', completion_time=timezone.now())
                        # transaction.on_commit(lambda: processing_queue.put([process_hm_image, [hm, microscope]]))

        elif len(squares) > 0:
            is_done = False
            square = squares[0]
            if square.status == 'queued' or square.status == 'started':
                logger.info('Waiting on square file')
                path = os.path.join(microscope.scope_path, square.raw)
                finder = square.finders.first()
                scope.square(finder.stage_x, finder.stage_y, finder.stage_z, file=square.raw)
                square = update(square, status='acquired', completion_time=timezone.now())
                # transaction.on_commit(lambda: processing_queue.put([process_square_image, [square, grid, microscope], {}]))
                process_square_image(square, grid, microscope)
        elif is_done:
            microscope_id = session.microscope_id.pk
            if os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'.pause_{microscope_id}')):
                paused = os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}')
                open(paused, 'w').close()
                update(grid, status='paused')
                logger.info('SerialEM is paused')
                while os.path.isfile(paused):

                    sys.stdout.flush()
                    time.sleep(3)
                next_file = os.path.join(os.getenv('TEMPDIR'), f'next_{microscope_id}')
                if os.path.isfile(next_file):
                    os.remove(next_file)
                    running = False
                else:
                    update(grid, status='started')
            else:
                running = False
        else:
            logger.debug(f'Waiting for incomplete processes, queue size: {processing_queue.qsize()}')
            processing_queue.join()
            logger.debug('All processes complete')
            is_done = True
        logger.debug(f'Running: {running}')
    else:
        update(grid, status='complete')
        logger.info('Grid finished')
        return 'finished'


def create_process(session):
    process = session.process_set.first()

    if process is None:
        process = Process(session_id=session, PID=os.getpid(), status='running')
        process = process.save()
        return process

    return update(process, PID=os.getpid(), status='running')


def process_square_image(square, grid, microscope_id):
    protocol = load_protocol(os.path.join(grid.directory, 'protocol.yaml'))
    plugins = load_plugins()
    params = grid.params_id
    is_bis = params.bis_max_distance > 0
    montage = None
    if square.status == 'acquired':
        montage = get_file_and_process(raw=square.raw, name=square.name, directory=microscope_id.scope_path)
        montage.export_as_png()
        targets, finder_method, classifier_method = find_targets(montage, load_protocol()['holeFinders'])
        targets = create_targets(targets, montage, target_type='hole')
        holes = add_targets(grid, square, targets, HoleModel, finder_method, classifier_method)

        square = update(square, status='processed', shape_x=montage.shape_x,
                        shape_y=montage.shape_y, pixel_size=montage.pixel_size, refresh_from_db=True)
        transaction.on_commit(lambda: logger.debug('targets added'))
    if square.status == 'processed':
        if montage is None:
            montage = Montage(name=square.name)
        selector_wrapper(protocol[f'{square.targets_prefix}Selectors'], square, n_groups=5, montage=montage)

        square = update(square, status='selected')
        transaction.on_commit(lambda: logger.debug('Selectors added'))
    if square.status == 'selected':
        if is_bis:
            holes = list(HoleModel.display.filter(square_id=square.square_id))
            holes = group_holes_for_BIS([h for h in holes if h.is_good(plugins=plugins) and not h.is_excluded(protocol, square.targets_prefix)[0]],
                                        max_radius=grid.params_id.bis_max_distance, min_group_size=grid.params_id.min_bis_group_size)
            for hole in holes:
                hole.save()
        logger.info(f'Picking holes on {square}')
        select_n_areas(square, grid.params_id.holes_per_square, is_bis=is_bis)
        square = update(square, status='targets_picked')
    if square.status == 'targets_picked':
        square = update(square, status='completed', completion_time=timezone.now())
    if square.status == 'completed':
        logger.info(f'Square {square.name} analysis is complete')


def process_hole_image(hole, microscope_id):
    montage = get_file_and_process(hole.raw, hole.name, directory=microscope_id.scope_path)
    montage.export_as_png(normalization=auto_contrast_sigma, binning_method=fourier_crop)
    update(hole, status='processed',
           pixel_size=montage.pixel_size,)


def write_sessionLock(session, lockFile):
    with open(lockFile, 'w') as f:
        f.write(session.session_id)


def autoscreen(session_id):
    session = ScreeningSession.objects.get(session_id=session_id)
    microscope = session.microscope_id
    lockFile, sessionLock = session.isScopeLocked
    add_log_handlers(directory=session.directory, name='run.out')
    logger.debug(f'Main Log handlers:{logger.handlers}')
    is_stop_file(session.session_id)
    if sessionLock is not None:
        logger.warning(
            f'\nThe requested microscope is busy.\n\tLock file {lockFile} found\n\tSession id: {sessionLock} is currently running.\n\tIf you are sure that the microscope is not running, remove the lock file and restart.\nExiting.')
        sys.exit(0)
    else:
        write_sessionLock(session, lockFile)
    process = create_process(session)
    try:
        grids = list(session.autoloadergrid_set.all().order_by('position'))
        logger.info(f'Process: {process}')
        logger.info(f'Session: {session}')
        logger.info(f"Grids: {', '.join([grid.__str__() for grid in grids])}")
        scopeInterface = SerialemInterface
        if microscope.serialem_IP == 'xxx.xxx.xxx.xxx':
            logger.info('Setting scope into test mode')
            scopeInterface = FakeScopeInterface

        with scopeInterface(ip=microscope.serialem_IP,
                            port=microscope.serialem_PORT,
                            energyfilter=session.detector_id.energy_filter,
                            directory=microscope.windows_path,
                            scope_path=microscope.scope_path,
                            loader_size=microscope.loader_size) as scope:
            # START image processing processes
            processing_queue = multiprocessing.JoinableQueue()
            child_process = multiprocessing.Process(target=processing_worker_wrapper, args=(session.directory, processing_queue,))
            child_process.start()
            logger.debug(f'Main Log handlers:{logger.handlers}')
            for grid in grids:
                status = run_grid(grid, session, processing_queue, scope)
            status = 'complete'
    except Exception as e:
        logger.exception(e)
        status = 'error'
    except KeyboardInterrupt:
        logger.info('Stopping Smartscope.py autoscreen')
        status = 'killed'
    finally:
        os.remove(lockFile)
        update(process, status=status)
        logger.debug('Wrapping up')
        processing_queue.put('exit')
        child_process.join()
        logger.debug('Process joined')
