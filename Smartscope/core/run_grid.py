import os
import sys
import time
import logging
from enum import Enum
from pathlib import Path
from django.utils import timezone
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

from .grid.grid_status import GridStatus
from .grid.finders import find_targets
from .grid.grid_io import GridIO
from .grid.run_io import get_file_and_process
from .grid.run_square import RunSquare
from .grid.run_hole import RunHole

from .interfaces.microscope_interface import MicroscopeInterface

from Smartscope.core.selectors import selector_wrapper
from Smartscope.core.models import ScreeningSession, SquareModel, AutoloaderGrid
from Smartscope.core.settings.worker import PROTOCOL_COMMANDS_FACTORY
from Smartscope.core.frames import get_frames_prefix, parse_frames_prefix
from Smartscope.core.mesh_rotation import calculate_hole_geometry
from Smartscope.core.status import status
from Smartscope.core.protocols import get_or_set_protocol
from Smartscope.core.preprocessing_pipelines import load_preprocessing_pipeline
from Smartscope.core.db_manipulations import update, queue_atlas, add_targets
from Smartscope.core.data_manipulations import select_n_areas

from Smartscope.lib.image_manipulations import export_as_png
    


def run_grid(
        grid:AutoloaderGrid,
        session:ScreeningSession,
        scope:MicroscopeInterface
    ): #processing_queue:multiprocessing.JoinableQueue,
    """Main logic for the SmartScope process
    Args:
        grid (AutoloaderGrid): AutoloadGrid object from Smartscope.server.models
        session (ScreeningSession): ScreeningSession object from Smartscope.server.models
    """
    logger.info(f'###Check status of grid, grid ID={grid.grid_id}.')
    session_id = session.pk
    microscope = session.microscope_id


    grid = update(grid, refresh_from_db=True, last_update=None)
    # Set the Websocket_update_decorator grid property
    update.grid = grid

    if grid.status == GridStatus.COMPLETED:
        logger.info(f'Grid {grid.name} already complete. grid ID={grid.grid_id}')
        return
    
    if grid.status == GridStatus.ABORTING:
        logger.info(f'Aborting {grid.name}')
        update(grid, status=GridStatus.COMPLETED)
        return

    logger.info(f'Starting {grid.name}, status={grid.status}') 
    if grid.status is GridStatus.NULL:
        grid = update(grid, status=GridStatus.STARTED, start_time=timezone.now())
    else:
        grid = update(grid, status=GridStatus.STARTED)

    GridIO.create_grid_directories(grid.directory)
    logger.info(f"create and the enter into Grid directory={grid.directory}")
    os.chdir(grid.directory)
    params = grid.params_id

    protocol = get_or_set_protocol(grid)
    preprocessing = load_preprocessing_pipeline(Path('preprocessing.json'))
    preprocessing.start(grid)
    is_stop_file(session_id)
    atlas = queue_atlas(grid)

    # scope

    # create frames directory
    prefix = parse_frames_prefix(get_frames_prefix(grid),grid)
    grid_dir = grid.frames_dir(prefix=prefix)
    if params.save_frames:
        GridIO.create_grid_frames_directory(session.detector_id.frames_directory, grid.frames_dir(prefix=prefix))
        logger.debug(f'Saving the frames in {grid_dir}')
    scope.loadGrid(grid.position)
    is_stop_file(session_id)
    scope.setup(params.save_frames,grid_dir=grid_dir,framesName=f'{session.date}_{grid.name}')
    scope.reset_state()

    # run acquisition
    if atlas.status == status.QUEUED or atlas.status == status.STARTED:
        atlas = update(atlas, status=status.STARTED)
        logger.info('Waiting on atlas file')
        runAcquisition(
            scope,
            protocol.atlas.acquisition,
            params,
            atlas
        )
        atlas = update(atlas,
            status=status.ACQUIRED,
            completion_time=timezone.now()
        )

    # find targets
    if atlas.status == status.ACQUIRED:
        logger.info('Atlas acquired')
        montage = get_file_and_process(
            raw=atlas.raw,
            name=atlas.name,
            directory=microscope.scope_path
        )
        export_as_png(montage.image, montage.png)
        targets, finder_method, classifier_method, _ = find_targets(
            montage,
            protocol.atlas.targets.finders
        )
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
    
    # 
    if atlas.status == status.PROCESSED:
        selector_wrapper(protocol.atlas.targets.selectors, atlas, n_groups=5)
        selected = select_n_areas(atlas, grid.params_id.squares_num)
        with transaction.atomic():
            for obj in selected:
                update(obj, selected=True, status='queued')
        atlas = update(atlas, status=status.COMPLETED)

        #Release atlas items from memory.
        if 'montage' in locals():
            del montage
        del atlas
    logger.info('Atlas analysis is complete')


    running = True
    is_done = False
    while running:
        is_stop_file(session_id)
        grid = update(grid, refresh_from_db=True, last_update=None)
        params = grid.params_id
        if grid.status == GridStatus.ABORTING:
            preprocessing.stop(grid)
            break
        else:
            square, hole = get_queue(grid)
            priority = get_target_priority(grid, (square, hole))
            logger.debug(f'Priority: {priority}')

        logger.info(f'Queued => Square: {square}, Hole: {hole}')
        logger.info(f'Targets done: {is_done}')
        if priority == TargetPriority.HOLE:
            is_done = False
            logger.info(f'Running Hole {hole}')
            # process medium image
            hole = update(hole, status=status.STARTED)
            runAcquisition(
                scope,
                protocol.mediumMag.acquisition,
                params,
                hole
            )
            if hole.status == status.SKIPPED:
                continue
            hole = update(hole,
                status=status.ACQUIRED,
                completion_time=timezone.now()
            )
            RunHole.process_hole_image(hole, grid, microscope)
            if hole.status == status.SKIPPED:
                continue

            scope.reset_image_shift_values(afis=params.afis)
            for hm in hole.targets.exclude(status__in=[status.ACQUIRED,status.COMPLETED]).order_by('hole_id__number'):
                hm = update(hm, refresh_from_db=False, status=status.STARTED)
                if hm.hole_id.status == status.SKIPPED:
                    break
                hm = runAcquisition(
                    scope,
                    protocol.highMag.acquisition,
                    params,
                    hm
                )
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
            scope.flash_cold_FEG(params.coldfegflash_delay)
        elif priority == TargetPriority.SQUARE:
            is_done = False
            logger.info(f'Running Square {square}')
            # process square
            if square.status == status.QUEUED or square.status == status.STARTED:
                square = update(square, status=status.STARTED)
                logger.info('Waiting on square file')
                runAcquisition(
                    scope,
                    protocol.square.acquisition,
                    params,
                    square
                )
                square = update(square, status=status.ACQUIRED, completion_time=timezone.now())
            RunSquare.process_square_image(square, grid, microscope)
            # calculate_hole_geometry(grid)
        elif is_done:
            microscope_id = session.microscope_id.pk
            tmp_file = os.path.join(settings.TEMPDIR, f'.pause_{microscope_id}')
            if os.path.isfile(tmp_file):
                paused = os.path.join(settings.TEMPDIR, f'paused_{microscope_id}')
                open(paused, 'w').close()
                update(grid, status=GridStatus.PAUSED)
                logger.info('SerialEM is paused')
                while os.path.isfile(paused):
                    sys.stdout.flush()
                    time.sleep(3)
                next_file = os.path.join(settings.TEMPDIR, f'next_{microscope_id}')
                if os.path.isfile(next_file):
                    os.remove(next_file)
                    running = False
                else:
                    update(grid, status=GridStatus.STARTED)
            else:
                running = False
        else:
            logger.debug('All processes complete')
            is_done = True
        logger.debug(f'Running: {running}')
    else:
        update(grid, status=GridStatus.COMPLETED)
        logger.info('Grid finished')
        return 'finished'

class TargetPriority(Enum):
    HOLE = 'hole'
    SQUARE = 'square'


def get_target_priority(grid, queue):
    square, hole = queue
    if hole is None and square is None:
        return
    if hole is None:
        return TargetPriority.SQUARE
    if square is None:
        return TargetPriority.HOLE
    if grid.collection_mode == 'screening' and grid.session_id.microscope_id.vendor != 'JEOL':
        return TargetPriority.HOLE
    return TargetPriority.SQUARE

    

def get_queue(grid):
    square = grid.squaremodel_set.filter(selected=True).\
        exclude(status__in=[status.SKIPPED, status.COMPLETED]).\
        order_by('number').first()
    hole = grid.holemodel_set.filter(selected=True, square_id__status=status.COMPLETED).\
        exclude(status__in=[status.SKIPPED, status.COMPLETED]).\
        order_by('square_id__completion_time', 'number').first()
    return square, hole#[h for h in holes if not h.bisgroup_acquired]


def is_stop_file(sessionid: str) -> bool:
    stop_file = os.path.join(settings.TEMPDIR, f'{sessionid}.stop')
    if os.path.isfile(stop_file):
        logger.debug(f'Stop file {stop_file} found.')
        os.remove(stop_file)
        raise KeyboardInterrupt()


def parse_method(method):
    if not isinstance(method, dict):
        logger.info(f'Running protocol method: {method}')
        return method, {}, [], {}
    args = []
    kwargs = dict()
    method_name, content = method.popitem()
    kwargs = content.pop('kwargs', {})
    args = content.pop('args', [])

    logger.info(f'Running protocol method: {method_name}, {content} with args={args} and kwargs={kwargs}')
    return method_name, content, args, kwargs
    

def runAcquisition(
        scope,
        methods,
        params,
        instance,
    ):
    for method in methods:
        method, content, args, kwargs = parse_method(method)
        output = PROTOCOL_COMMANDS_FACTORY[method](scope,params,instance, content, *args, **kwargs)
    return output