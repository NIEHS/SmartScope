
import os
from random import random
import sys
import time
import shlex
from Smartscope.core.microscope_interfaces import FakeScopeInterface, TFSSerialemInterface, JEOLSerialemInterface
from Smartscope.core.selectors import selector_wrapper
from Smartscope.core.models import ScreeningSession, HoleModel, SquareModel, Process, HighMagModel
from Smartscope.core.settings.worker import PROTOCOLS_FACTORY
from Smartscope.lib.image_manipulations import auto_contrast_sigma, fourier_crop, export_as_png
from Smartscope.lib.montage import Montage,create_targets_from_center
from Smartscope.core.finders import find_targets
from Smartscope.lib.preprocessing_methods import processing_worker_wrapper
from Smartscope.lib.file_manipulations import get_file_and_process, create_grid_directories
from Smartscope.lib.transformations import register_stage_to_montage, register_targets_by_proximity
from Smartscope.core.db_manipulations import update, select_n_areas, queue_atlas, add_targets, group_holes_for_BIS, set_or_update_refined_finder
from Smartscope.lib.logger import add_log_handlers
from Smartscope.lib.diagnostics import generate_diagnostic_figure
from math import cos, radians
from django.db import transaction
from django.utils import timezone
import multiprocessing
import logging
import subprocess
import numpy as np
from pathlib import Path


logger = logging.getLogger(__name__)


def get_queue(grid):
    """Query database to refresh the queue

    Args:
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models

    Returns:
        (list): [squares,holes]; List of SquareModels that are status='queued' and List of HoleModels that are status='queued'
    """
    squares = list(grid.squaremodel_set.filter(selected=True, status__in=['queued', 'started']).order_by('number'))
    holes = list(grid.holemodel_set.filter(selected=True, square_id__status='completed').exclude(status='completed').order_by('square_id__completion_time', 'number'))
    logger.debug(f'Pre-queue Holes: {holes}')
    return squares, holes#[h for h in holes if not h.bisgroup_acquired]


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
    if grid.status == 'aborting':
        logger.info(f'Aborting {grid.name}')
        return

    session_id = session.pk
    microscope = session.microscope_id

    # Set the Websocket_update_decorator grid property
    update.grid = grid

    logger.info(f'Starting {grid.name}') 

    grid = update(grid, refresh_from_db=True, last_update=None)

    if grid.status is None:
        grid = update(grid, status='started', start_time=timezone.now())

    create_grid_directories(grid.directory)
    os.chdir(grid.directory)
    processing_queue.put([os.chdir, [grid.directory], {}])
    params = grid.params_id
    # ADD the new protocol loader
    protocol = PROTOCOLS_FACTORY[grid.protocol]

    resume_incomplete_processes(processing_queue, grid, session.microscope_id)
    subprocess.Popen(shlex.split(f'smartscope.py highmag_processing smartscopePipeline {grid.grid_id} 1'))
    is_stop_file(session_id)
    atlas = queue_atlas(grid)

    scope.loadGrid(grid.position)
    is_stop_file(session_id)
    scope.setup(params.save_frames, params.zeroloss_delay, framesName=f'{session.date}_{grid.name}')
    scope.clear_hole_ref()
    grid_type = grid.holeType
    grid_mesh = grid.meshMaterial
    if atlas.status == 'queued' or atlas.status == 'started':
        atlas = update(atlas, status='started')
        print('Waiting on atlas file')
        path = os.path.join(microscope.scope_path, atlas.raw)
        scope.atlas(mag=session.detector_id.atlas_mag, c2=session.detector_id.c2_perc, spotsize=session.detector_id.spot_size,
                    tileX=params.atlas_x, tileY=params.atlas_y, file=atlas.raw)
        atlas = update(atlas, status='acquired', completion_time=timezone.now())

    if atlas.status == 'acquired':
        logger.info('Atlas acquired')
        montage = get_file_and_process(raw=atlas.raw, name=atlas.name, directory=microscope.scope_path)
        export_as_png(montage.image, montage.png)
        targets, finder_method, classifier_method, _ = find_targets(montage, protocol.squareFinders)
        squares = add_targets(grid, atlas, targets, SquareModel, finder_method, classifier_method)
        atlas = update(atlas, status='processed', pixel_size=montage.pixel_size,
                       shape_x=montage.shape_x, shape_y=montage.shape_y, stage_z=montage.stage_z)
    if atlas.status == 'processed':
        selector_wrapper(protocol.squareSelectors, atlas, n_groups=5)
        select_n_areas(atlas, grid.params_id.squares_num)
        atlas = update(atlas, status='completed')

    logger.info('Atlas analysis is complete')

    running = True
    is_done = False
    while running:
        is_stop_file(session_id)
        grid = update(grid, refresh_from_db=True, last_update=None)
        params = grid.params_id
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
            hole = update(hole, status='started')
            iteration = 0
            while True:
                is_stop_file(session_id)
                scope.lowmagHole(stage_x, stage_y, stage_z, round(params.tilt_angle, 1),
                                    file=hole.raw, hole_size_in_um=grid.holeType.hole_size)
                hole = update(hole, status='acquired',completion_time=timezone.now())
                recenter = process_hole_image(hole, grid, microscope,iteration)
                iteration +=1
                if recenter is None:
                    set_or_update_refined_finder(hole.hole_id, stage_x, stage_y, stage_z)
                    break
                logger.debug(f'Recenter value in pixels = {recenter}')
                stage_x, stage_y, stage_z = scope.align_to_coord(recenter)
            scope.focusDrift(params.target_defocus_min, params.target_defocus_max, params.step_defocus, params.drift_crit)
            scope.reset_image_shift_values()
            for hm in hole.targets.exclude(status__in=['acquired','completed']).order_by('hole_id__number'):
                update(hm, status='started')
                finder = hm.finders.first()
                offset = 0
                if params.offset_targeting and (grid.collection_mode == 'screening' or params.offset_distance != -1) and grid_type.hole_size is not None:
                    offset = add_IS_offset(grid_type.hole_size, grid_mesh.name, offset_in_um=params.offset_distance)
                isX, isY = stage_x - finder.stage_x + offset, (stage_y - finder.stage_y) * cos(radians(round(params.tilt_angle, 1)))
                frames = scope.highmag(isX, isY, round(params.tilt_angle, 1), file=hm.raw,
                                        frames=params.save_frames, earlyReturn=any([params.force_process_from_average, params.save_frames is False]))
                hm = update(hm, is_x=isX, is_y=isY, offset=offset, frames=frames, status='acquired', completion_time=timezone.now())
                if hm.hole_id.bis_type != 'center':
                    update(hm.hole_id, status='acquired', completion_time=timezone.now())
            update(hole, status='completed')
        elif len(squares) > 0:
            is_done = False
            square = squares[0]
            if square.status == 'queued' or square.status == 'started':
                square = update(square, status='started')
                logger.info('Waiting on square file')
                finder = square.finders.first()
                stageX, stageY, stageZ = scope.square(finder.stage_x, finder.stage_y, finder.stage_z, file=square.raw)
                square = update(square, status='acquired', completion_time=timezone.now())
                set_or_update_refined_finder(square.square_id, stageX, stageY, stageZ)
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
    protocol = PROTOCOLS_FACTORY[grid.protocol]
    params = grid.params_id
    is_bis = params.bis_max_distance > 0
    montage = None
    if square.status == 'acquired':
        montage = get_file_and_process(raw=square.raw, name=square.name, directory=microscope_id.scope_path)
        export_as_png(montage.image, montage.png)
        targets, finder_method, classifier_method, _ = find_targets(montage, protocol.holeFinders)
        holes = add_targets(grid, square, targets, HoleModel, finder_method, classifier_method)

        square = update(square, status='processed', shape_x=montage.shape_x,
                        shape_y=montage.shape_y, pixel_size=montage.pixel_size, refresh_from_db=True)
        transaction.on_commit(lambda: logger.debug('targets added'))
    if square.status == 'processed':
        if montage is None:
            montage = Montage(name=square.name)
            montage.load_or_process()
        selector_wrapper(protocol.holeSelectors, square, n_groups=5, montage=montage)

        square = update(square, status='selected')
        transaction.on_commit(lambda: logger.debug('Selectors added'))
    if square.status == 'selected':
        if is_bis:
            holes = list(HoleModel.display.filter(square_id=square.square_id))
            holes = group_holes_for_BIS([h for h in holes if h.is_good() and not h.is_excluded()[0]],
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


def check_if_need_recenter(targets,montage, threshold_in_microns):
    coords_in_microns = np.array([(target.coords - montage.center) * montage.pixel_size/10_000 for target in targets])
    dist_to_center = np.sqrt(np.sum(np.power(coords_in_microns,2),axis=1))
    smallest_distance_ind = np.argmin(dist_to_center)
    small_dist_to_center = dist_to_center[smallest_distance_ind]
    if small_dist_to_center > threshold_in_microns:
        return  targets[smallest_distance_ind].coords, True
    return targets[smallest_distance_ind].coords, False

def process_hole_image(hole, grid, microscope_id,iteration):
    protocol = PROTOCOLS_FACTORY[grid.protocol]
    montage = get_file_and_process(hole.raw, hole.name, directory=microscope_id.scope_path, force_reprocess=True)
    export_as_png(montage.image, montage.png, normalization=auto_contrast_sigma, binning_method=fourier_crop)
    if hole.bis_group is not None:
        hole_group = list(HoleModel.objects.filter(square_id=hole.square_id,bis_group=hole.bis_group))
    else:
        hole_group = [hole]
    hole.targets.delete()
    image_coords = register_stage_to_montage(np.array([x.stage_coords for x in hole_group]),hole.stage_coords,montage.center,montage.pixel_size,montage.rotation_angle)
    if len(protocol.highmagFinders) != 0:
        targets, finder_method, classifier_method, additional_outputs = find_targets(montage, protocol.highmagFinders)
        coords, is_recenter_required = check_if_need_recenter(targets,montage,0.7)
        generate_diagnostic_figure(montage.image,[([montage.center],(0,255,0), 1), ([coords],(255,0,0),2),([t.coords for t in targets],(0,0,255),1)],Path(montage.directory / f'hole_recenter_it{iteration}.png'))
        if is_recenter_required:
            logger.debug('Need recentering')
            return coords - montage.center
    else:
        targets = create_targets_from_center(image_coords, montage)
        finder_method = 'Registration'
        classifier_method=None
    
    # if len(hole_group) > 1:
    register = register_targets_by_proximity(image_coords,[target.coords for target in targets])
    for h, index in zip(hole_group,register):
        target = targets[index]
        add_targets(grid,h,[target],HighMagModel,finder_method,classifier=classifier_method)
    # else:
    #     add_targets(grid,hole_group[0],targets,HighMagModel,finder_method,classifier=classifier_method )

    update(hole, shape_x=montage.shape_x,
                        shape_y=montage.shape_y, pixel_size=montage.pixel_size, status='processed')


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
        scopeInterface = TFSSerialemInterface
        if microscope.serialem_IP == 'xxx.xxx.xxx.xxx':
            logger.info('Setting scope into test mode')
            scopeInterface = FakeScopeInterface

        if session.microscope_id.vendor == 'JEOL':
            logger.info('Using the JEOL interface')
            scopeInterface = JEOLSerialemInterface

        with scopeInterface(ip=microscope.serialem_IP,
                            port=microscope.serialem_PORT,
                            energyfilter=session.detector_id.energy_filter,
                            directory=microscope.windows_path,
                            frames_directory=session.detector_id.frames_windows_directory,
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
