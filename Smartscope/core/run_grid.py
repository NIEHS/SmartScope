
from numpy.typing import ArrayLike
from typing import List, Union
import os
import sys
import time
from django.db import transaction
from django.utils import timezone
import multiprocessing
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


from .diagnostics import generate_diagnostic_figure, Timer
from .interfaces.microscope_interface import MicroscopeInterface
from .transformations import register_to_other_montage, register_targets_by_proximity
from Smartscope.core.selectors import selector_wrapper
from Smartscope.core.models import ScreeningSession, HoleModel, SquareModel, HighMagModel, AutoloaderGrid
from Smartscope.core.settings.worker import PROTOCOL_COMMANDS_FACTORY
from Smartscope.core.finders import find_targets
from Smartscope.core.status import status, grid_status
from Smartscope.core.protocols import get_or_set_protocol
from Smartscope.core.preprocessing_pipelines import load_preprocessing_pipeline
from Smartscope.core.db_manipulations import update, select_n_areas, queue_atlas, add_targets, group_holes_for_BIS


from Smartscope.lib.image_manipulations import auto_contrast_sigma, fourier_crop, export_as_png
from Smartscope.lib.image.montage import Montage
from Smartscope.lib.image.targets import Targets
from Smartscope.lib.image.target import Target
from Smartscope.lib.file_manipulations.grid_io import GridIO



# for arguments
from Smartscope.lib.multishot import MultiShot


def run_grid(
        grid:AutoloaderGrid,
        session:ScreeningSession,
        processing_queue:multiprocessing.JoinableQueue,
        scope:MicroscopeInterface
    ):
    """Main logic for the SmartScope process
    Args:
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models
        session (ScreeningSession): ScreeningSession object from Smartscope.server.models
    """
    logger.info(f'###Check status of grid, grid ID={grid.grid_id}.')
    session_id = session.pk
    microscope = session.microscope_id

    # Set the Websocket_update_decorator grid property
    update.grid = grid
    if grid.status == grid_status.COMPLETED:
        logger.info(f'Grid {grid.name} already complete. grid ID={grid.grid_id}')
        return
    if grid.status == grid_status.ABORTING:
        logger.info(f'Aborting {grid.name}')
        update(grid, status=grid_status.COMPLETED)
        return

    logger.info(f'Starting {grid.name}, status={grid.status}') 
    grid = update(grid, refresh_from_db=True, last_update=None)

    if grid.status is grid_status.NULL:
        grid = update(grid, status=grid_status.STARTED, start_time=timezone.now())

    GridIO.create_grid_directories(grid.directory)
    os.chdir(grid.directory)
    # print('###grid directory:', grid.directory)
    processing_queue.put([os.chdir, [grid.directory], {}])
    params = grid.params_id

    # ADD the new protocol loader
    protocol = get_or_set_protocol(grid)
    resume_incomplete_processes(processing_queue, grid, session.microscope_id)
    preprocessing = load_preprocessing_pipeline(Path('preprocessing.json'))
    preprocessing.start(grid)
    is_stop_file(session_id)
    atlas = queue_atlas(grid)
    scope.loadGrid(grid.position)
    is_stop_file(session_id)
    scope.setup(params.save_frames, framesName=f'{session.date}_{grid.name}')
    scope.reset_state()
    # grid_type = grid.holeType
    # grid_mesh = grid.meshMaterial
    
    if atlas.status == status.QUEUED or atlas.status == status.STARTED:
        atlas = update(atlas, status=status.STARTED)
        logger.info('Waiting on atlas file')
        runAcquisition(scope,protocol.atlas.acquisition,params,atlas)
        atlas = update(atlas, status=status.ACQUIRED, completion_time=timezone.now())
    if atlas.status == status.ACQUIRED:
        logger.info('Atlas acquired')
        montage = get_file_and_process(raw=atlas.raw, name=atlas.name, directory=microscope.scope_path)
        export_as_png(montage.image, montage.png)
        targets, finder_method, classifier_method, _ = find_targets(montage, protocol.atlas.targets.finders)
        squares = add_targets(
            grid,
            atlas,
            targets,
            SquareModel,
            finder_method,
            classifier_method
        )
        atlas = update(atlas,
            status=status.PROCESSED,
            pixel_size=montage.pixel_size,
            shape_x=montage.shape_x,
            shape_y=montage.shape_y,
            stage_z=montage.stage_z
        )
    if atlas.status == status.PROCESSED:
        selector_wrapper(protocol.atlas.targets.selectors, atlas, n_groups=5)
        select_n_areas(atlas, grid.params_id.squares_num)
        atlas = update(atlas, status=status.COMPLETED)

    logger.info('Atlas analysis is complete')

    running = True
    is_done = False
    while running:
        is_stop_file(session_id)
        grid = update(grid, refresh_from_db=True, last_update=None)
        params = grid.params_id
        if grid.status == grid_status.ABORTING:
            preprocessing.stop(grid)
            break
        else:
            square, hole = get_queue(grid)
        if hole is not None and (square is None or grid.collection_mode == 'screening'):
            is_done = False
            hole = update(hole, status=status.STARTED)
            runAcquisition(
                scope,
                protocol.mediumMag.acquisition,
                params,
                hole
            )
            hole = update(hole,
                status=status.ACQUIRED,
                completion_time=timezone.now()
            )
            process_hole_image(hole, grid, microscope)
            scope.focusDrift(
                params.target_defocus_min,
                params.target_defocus_max,
                params.step_defocus,
                params.drift_crit
            )
            scope.reset_image_shift_values()
            for hm in hole.targets.exclude(status__in=[status.ACQUIRED,status.COMPLETED]).order_by('hole_id__number'):
                hm = update(hm, status=status.STARTED)
                hm = runAcquisition(scope,protocol.highMag.acquisition,params,hm)
                hm = update(hm,
                    status=status.ACQUIRED,
                    completion_time=timezone.now(),
                    extra_fields=['is_x','is_y','offset','frames']
                )
                if hm.hole_id.bis_type != 'center':
                    update(hm.hole_id, status=status.ACQUIRED, completion_time=timezone.now())
            update(hole, status=status.COMPLETED)
            scope.reset_AFIS_image_shift(afis=params.afis)
            scope.refineZLP(params.zeroloss_delay)
            scope.collectHardwareDark(params.hardwaredark_delay)
        elif square is not None:
            is_done = False
            if square.status == status.QUEUED or square.status == status.STARTED:
                square = update(square, status=status.STARTED)
                logger.info('Waiting on square file')
                runAcquisition(scope,protocol.square.acquisition,params,square)
                square = update(square, status=status.ACQUIRED, completion_time=timezone.now())
                process_square_image(square, grid, microscope)
        elif is_done:
            microscope_id = session.microscope_id.pk
            if os.path.isfile(os.path.join(os.getenv('TEMPDIR'), f'.pause_{microscope_id}')):
                paused = os.path.join(os.getenv('TEMPDIR'), f'paused_{microscope_id}')
                open(paused, 'w').close()
                update(grid, status=grid_status.PAUSED)
                logger.info('SerialEM is paused')
                while os.path.isfile(paused):
                    sys.stdout.flush()
                    time.sleep(3)
                next_file = os.path.join(os.getenv('TEMPDIR'), f'next_{microscope_id}')
                if os.path.isfile(next_file):
                    os.remove(next_file)
                    running = False
                else:
                    update(grid, status=grid_status.STARTED)
            else:
                running = False
        else:
            logger.debug(f'Waiting for incomplete processes, queue size: {processing_queue.qsize()}')
            processing_queue.join()
            logger.debug('All processes complete')
            is_done = True
        logger.debug(f'Running: {running}')
    else:
        update(grid, status=grid_status.COMPLETED)
        logger.info('Grid finished')
        return 'finished'



def get_queue(grid):
    square = grid.squaremodel_set.\
        filter(selected=True, status__in=[status.QUEUED, status.STARTED]).\
        order_by('number').first()
    hole = grid.holemodel_set.filter(selected=True, square_id__status=status.COMPLETED).\
        exclude(status=status.COMPLETED).\
        order_by('square_id__completion_time', 'number').first()
    return square, hole#[h for h in holes if not h.bisgroup_acquired]



def resume_incomplete_processes(queue, grid, microscope_id):
    """Query database for models with incomplete processes and adds them to the processing queue

    Args:
        queue (multiprocessing.JoinableQueue): multiprocessing queue of objects
          for processing by    the processing_worker
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models
        session (ScreeningSession): ScreeningSession object from Smartscope.server.models
    """
    squares = grid.squaremodel_set.filter(selected=1).exclude(
        status__in=[status.QUEUED, status.STARTED, status.COMPLETED]).order_by('number')
    holes = grid.holemodel_set.filter(selected=1).exclude(status__in=[status.QUEUED, \
        status.STARTED, status.PROCESSED, status.COMPLETED]).\
        order_by('square_id__number', 'number')
    for square in squares:
        logger.info(f'Square {square} was not fully processed')
        renew_queue = [process_square_image, [square, grid, microscope_id], {}]
        transaction.on_commit(lambda: queue.put(renew_queue))



def is_stop_file(sessionid: str) -> bool:
    stop_file = os.path.join(os.getenv('TEMPDIR'), f'{sessionid}.stop')
    if os.path.isfile(stop_file):
        logger.debug(f'Stop file {stop_file} found.')
        os.remove(stop_file)
        raise KeyboardInterrupt()


def runAcquisition(scope,methods,params,instance):
    for method in methods:
        output = PROTOCOL_COMMANDS_FACTORY[method](scope,params,instance)
    return output


def process_square_image(square, grid, microscope_id):
    protocol = get_or_set_protocol(grid).square.targets
    params = grid.params_id
    is_bis = params.bis_max_distance > 0
    montage = None
    if square.status == status.ACQUIRED:
        montage = get_file_and_process(
            raw=square.raw,
            name=square.name,
            directory=microscope_id.scope_path
        )
        export_as_png(montage.image, montage.png)
        targets, finder_method, classifier_method, _ = find_targets(montage, protocol.finders)
        holes = add_targets(grid, square, targets, HoleModel, finder_method, classifier_method)

        square = update(square,
            status=status.PROCESSED,
            shape_x=montage.shape_x,
            shape_y=montage.shape_y,
            pixel_size=montage.pixel_size,
            refresh_from_db=True
        )
        transaction.on_commit(lambda: logger.debug('targets added'))
    if square.status == status.PROCESSED:
        if montage is None:
            montage = Montage(name=square.name)
            montage.load_or_process()
        selector_wrapper(protocol.selectors, square, n_groups=5, montage=montage)
        square = update(square, status=status.TARGETS_SELECTED)
        transaction.on_commit(lambda: logger.debug('Selectors added'))
    if square.status == status.TARGETS_SELECTED:
        if is_bis:
            holes = list(HoleModel.display.filter(square_id=square.square_id))
            holes = group_holes_for_BIS(
                [h for h in holes if h.is_good() and not h.is_excluded()[0]],
                max_radius=grid.params_id.bis_max_distance,
                min_group_size=grid.params_id.min_bis_group_size
            )
            for hole in holes:
                hole.save()
        logger.info(f'Picking holes on {square}')
        select_n_areas(square, grid.params_id.holes_per_square, is_bis=is_bis)
        square = update(square, status=status.TARGETS_PICKED)
    if square.status == status.TARGETS_PICKED:
        square = update(square,
            status=status.COMPLETED,
            completion_time=timezone.now()
        )
    if square.status == status.COMPLETED:
        logger.info(f'Square {square.name} analysis is complete')


def process_hole_image(hole, grid, microscope_id):
    with Timer(text='Processing hole') as timer:
        protocol = get_or_set_protocol(grid).mediumMag
        params = grid.params_id
        logger.debug(f'Acquisition parameters: {params.params_id}')
        mutlishot_file = Path(grid.directory,'multishot.json')
        multishot = load_multishot_from_file(mutlishot_file)
        if multishot is not None:
            logger.info(f'Multishot enabled: {params.multishot_per_hole}, ' + \
                'Shots: {multishot.shots}, File: {mutlishot_file}')
        montage = get_file_and_process(
            hole.raw,
            hole.name,
            directory=microscope_id.scope_path,
            force_reprocess=True
        )
        export_as_png(
            montage.image,
            montage.png,
            normalization=auto_contrast_sigma,
            binning_method=fourier_crop
        )
        timer.report_timer('Getting and processing montage')
        if hole.bis_group is not None:
            hole_group = list(HoleModel.display.filter(square_id=hole.square_id,bis_group=hole.bis_group))
        else:
            hole_group = [hole]
        hole.targets.delete()
        timer.report_timer('Querying and deleting previous targerts in BIS group')
        square_montage = Montage(name=hole.square_id.name,working_dir=hole.grid_id.directory)
        square_montage.load_or_process()
        image_coords = register_to_other_montage(np.array([x.coords for x in hole_group]),hole.coords, montage, square_montage)
        timer.report_timer('Initial registration to the higher mag image')
        targets = []
        finder_method = 'Registration'
        classifier_method=None
        if len(protocol.targets.finders) != 0:
            targets, finder_method, classifier_method, additional_outputs = find_targets(montage, protocol.targets.finders)
            generate_diagnostic_figure(
                montage.image,
                [([montage.center],(0,255,0), 1), ([t.coords for t in targets],(0,0,255),1)],
                Path(montage.directory / f'hole_recenter_it.png')
            )
            
        if len(protocol.targets.finders) == 0 or targets == []:
            targets = Targets.create_targets_from_center(image_coords, montage)
        timer.report_timer('Identifying and registering targets')
        
        register = register_targets_by_proximity(
            image_coords,
            [target.coords for target in targets]
        )
        for h, index in zip(hole_group,register):
            target = targets[index]
            if not params.multishot_per_hole:
                targets_to_register=[target]
            else:
                targets_to_register= split_target_for_multishot(multishot,target.coords,montage)
            add_targets(
                grid,
                h,
                targets_to_register,
                HighMagModel,
                finder_method,
                classifier=classifier_method
            )
        timer.report_timer('Final registration and saving to db')
        update(hole,
            shape_x=montage.shape_x,
            shape_y=montage.shape_y,
            pixel_size=montage.pixel_size,
            status=status.PROCESSED
        )

def load_multishot_from_file(file:Union[str,Path]) -> Union[MultiShot,None]:
    if Path(file).exists():
        return MultiShot.parse_file(file)
    


def split_target_for_multishot(
        shots:MultiShot,
        target_coords:ArrayLike,
        montage: Montage
    ) -> List[Target]:
    shots_in_pixels = shots.convert_shots_to_pixel(montage.pixel_size / 10_000) + target_coords
    return Targets.create_targets_from_center(shots_in_pixels,montage)


def get_file_and_process(raw, name, directory='', force_reprocess=False):
    if force_reprocess or not os.path.isfile(raw):
        path = os.path.join(directory, raw)
        get_file(path, remove=True)
    montage = Montage(name)
    montage.load_or_process(force_process=force_reprocess)
    return montage



# def print_queue(squares, holes, session):
#     """Prints Queue to a file for displaying to the frontend

#     Args:
#         squares (list): list of squares returned from the get_queue method
#         holes (list): list of holes returned from the get_queue method
#         session (ScreeningSession): ScreeningSession object from Smartscope.server.models
#     """
#     string = ['------------------------------------------------------------\nCURRENT QUEUE:\n------------------------------------------------------------\nSquares:\n']
#     for s in squares:
#         string.append(f"\t{s.number} -> {s.name}\n")
#     string.append(f'------------------------------------------------------------\nHoles: (total={len(holes)})\n')
#     for h in holes:
#         string.append(f"\t{h.number} -> {h.name}\n")
#     string.append('------------------------------------------------------------\n')
#     string = ''.join(string)
#     with open(os.path.join(session.directory, 'queue.txt'), 'w') as f:
#         f.write(string)

