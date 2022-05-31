
import os
import signal
import sys
from Smartscope.core.microscope_interfaces import FakeScopeInterface, SerialemInterface
from Smartscope.core.selectors import selector_wrapper
from Smartscope.core.models import *
from Smartscope.server.api.serializers import *
from Smartscope.lib.file_manipulations import *
from Smartscope.core.db_manipulations import *
from Smartscope.lib.config import *
from django.db import transaction
from django.utils import timezone
from math import cos, radians, floor, sqrt
import multiprocessing
import logging
from Smartscope.lib.converters import *
from Smartscope.server.api.serializers import *
from django.core.cache import cache

logger = logging.getLogger(__name__)


def add_log_handlers(directory: str, name: str) -> None:
    main_handler = logging.FileHandler(os.path.join(directory, name), mode='a', encoding='utf-8')
    main_handler.setFormatter(logger.parent.handlers[0].formatter)
    logging.getLogger('Smartscope').addHandler(main_handler)


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
    high_mag = grid.highmagmodel_set.exclude(status__in=['queued', 'started', 'completed']).order_by('number')
    for square in squares:
        logger.info(f'Square {square} was not fully processed')
        transaction.on_commit(lambda: queue.put([process_square_image, [square, grid, microscope_id]]))
    for hole in holes:
        logger.info(f'Hole {hole} was not fully processed')
        transaction.on_commit(lambda: queue.put([process_hole_image, [hole, microscope_id]]))
    for hm in high_mag:
        logger.info(f'High_mag {hm} was not fully processed')
        transaction.on_commit(lambda: queue.put([process_hm_image, [hm, microscope_id, grid.params_id.save_frames]]))


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
        return True
    return False


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
    # try:
    # Set the Websocket_update_decorator grid property
    processing_queue.put(['set_update', [grid]])
    update.grid = grid

    logger.info(f'Starting {grid.name}')  # \nHoleType: {grid.holeType.name}

    # logger.debug(f'{grid.hole_finders}')
    # logger.debug(grid.square_finders)
    grid = update(grid, refresh_from_db=True, last_update=None)

    if grid.status is None:
        grid = update(grid, status='started', start_time=timezone.now())
    os.chdir(session.directory)
    grid.create_dir()
    processing_queue.put([os.chdir, [os.path.join(grid.directory)]])

    # ADD the new protocl loader
    protocol = load_protocol_wrapper(grid.protocol)
    save_protocol(protocol)

    resume_incomplete_processes(processing_queue, grid, session.microscope_id)

    atlas = queue_atlas(grid)
    params = grid.params_id
    scope.loadGrid(grid.position)
    scope.setup(params.save_frames, params.zeroloss_delay)
    if atlas.status == 'queued' or atlas.status == 'started':
        atlas = update(atlas, status='started')
        print('Waiting on atlas file')
        path = os.path.join(session.microscope_id.scope_path, atlas.raw)
        scope.atlas(mag=session.detector_id.atlas_mag, c2=session.detector_id.c2_perc, spotsize=session.detector_id.spot_size,
                    tileX=params.atlas_x, tileY=params.atlas_y, file=atlas.raw)
        # create_serialem_script('atlas', session, grids=grid, sele=atlas)
        get_file(path, remove=True)
        atlas = update(atlas, status='acquired')
        # grid = update(grid, last_update=None)

    if atlas.status == 'acquired':
        logger.info('Atlas acquired')
        montage, _ = process_montage(atlas, mag_level='atlas')
        montage.find_targets(load_protocol()['squareFinders'])
        targets = montage.create_targets()
        squares = add_targets(grid, atlas, targets, SquareModel)
        atlas = update(atlas, status='processed', pixel_size=montage.pixel_size,
                       shape_x=montage.shape_x, shape_y=montage.shape_y, stage_z=montage.stage_z)
        # grid = update(grid, last_update=None)
    if atlas.status == 'processed':
        selector_wrapper(protocol[f'{atlas.targets_prefix}Selectors'], atlas, n_groups=5)
        select_n_areas(atlas, grid.params_id.squares_num)
        atlas = update(atlas, status='targets_picked')
        # grid = update(grid, last_update=None)
    if atlas.status == 'targets_picked':
        # plot_atlas(atlas)
        atlas = update(atlas, status='completed', completion_time=timezone.now())
        # grid = update(grid, last_update=None)
    if atlas.status == 'completed':
        logger.info('Atlas analysis is complete')
    # raise Exception('Atlas done, exit')
    running = True
    restarting = True
    is_done = False
    while running:
        if is_stop_file(session_id):
            return 'stopped'
        grid = update(grid, refresh_from_db=True, last_update=None)
        params = grid.params_id
        is_bis = params.bis_max_distance > 0
        if grid.status == 'aborting':
            running = False
            squares, holes = [], []
        else:
            squares, holes = get_queue(grid)
        print_queue(squares, holes, session)
        if len(holes) > 0 and (len(squares) == 0 or grid.collection_mode == 'screening'):
            is_done = False
            hole = holes[0]
            finder = hole.finders.first()
            stage_x, stage_y, stage_z = finder.stage_x, finder.stage_y, finder.stage_z
            if is_bis and hole.bis_group is not None:
                bis_holes = list(grid.holemodel_set(manager='display').filter(bis_group=hole.bis_group,
                                                                              bis_type='is_area').exclude(status__in=['acquired', 'completed']))
                # bis_holes = [h for h in bis_holes if h.quality in [None, '0', '1']]
                bis_holes += [hole]
            else:
                bis_holes = [hole]

            if hole.status == 'queued' or hole.status == 'started':
                restarting = False
                hole = update(hole, status='started')

                scope.lowmagHole(stage_x, stage_y, stage_z, round(params.tilt_angle, 1),
                                 file=hole.raw, is_negativestain=grid.holeType.name in ['NegativeStain', 'Lacey'])
                currentDefocus = scope.focusDrift(params.target_defocus_min, params.target_defocus_max, params.step_defocus, params.drift_crit)
                hole = update(hole, status='acquired')
                # grid = update(grid, last_update=None)
                transaction.on_commit(lambda: processing_queue.put([process_hole_image, [hole, session.microscope_id]]))
            if hole.status in ['acquired', 'processed']:
                if restarting:
                    restarting = False
                    # processin_queue.put(process_hole_image(hole))
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
                        isX, isY = stage_x - finder.stage_x, (stage_y - finder.stage_y) * cos(radians(round(params.tilt_angle, 1)))
                        frames = scope.highmag(isX, isY, round(params.tilt_angle, 1), file=hm.raw, frames=params.save_frames)
                        # if out is not None:
                        #     frames = out
                        # else:
                        #     frames = None
                        hm = update(hm, is_x=isX, is_y=isY, frames=frames, status='acquired')
                        if h != hole:
                            update(h, status='acquired')
                        transaction.on_commit(lambda: processing_queue.put([process_hm_image, [hm, session.microscope_id]]))

        elif len(squares) > 0:
            is_done = False
            square = squares[0]
            if square.status == 'queued' or square.status == 'started':
                logger.info('Waiting on square file')
                path = os.path.join(session.microscope_id.scope_path, square.raw)
                finder = square.finders.first()
                scope.square(finder.stage_x, finder.stage_y, finder.stage_z, file=square.raw)
                square = update(square, status='acquired')
                # transaction.on_commit(lambda: processing_queue.put([process_square_image, [square, grid, session.microscope_id]]))
                process_square_image(square, grid, session.microscope_id)
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
    # except Exception as err:
    #     logger.exception(err)
    #     error = True
    # except KeyboardInterrupt as err:
    #     logger.info('Stopping main process')
    #     error = True


def create_process(session):
    process = session.process_set.first()
    # logger.debug(f'Trying to fetch process from db: {process}')
    if process is None:
        # logger.debug(f'process not found, creating new one')
        process = Process(session_id=session, PID=os.getpid(), status='running')
        process = process.save()
        return process

    return update(process, PID=os.getpid(), status='running')


def get_file_and_process(item, mag_level, directory=''):
    if not os.path.isfile(item.raw):
        path = os.path.join(directory, item.raw)
        get_file(path, remove=True)
    montage, _ = process_montage(item, mag_level=mag_level)
    return montage


def processing_worker_wrapper(logdir, queue,):
    logging.getLogger('Smartscope').handlers.pop()
    logger.debug(f'Log handlers:{logger.handlers}')
    add_log_handlers(directory=logdir, name='proc.out')
    logger.debug(f'Log handlers:{logger.handlers}')
    try:
        while True:
            logger.debug(f'Approximate processing queue size: {queue.qsize()}')
            item = queue.get()
            logger.debug(f'Got item {item} from queue')
            if 'set_update' in item:
                update.grid = item[1][0]
                queue.task_done()
                continue
            if item == 'exit':
                break
            if item is not None:
                logger.debug(f'Running {item[0]} {item[1]} from queue')
                item[0](*item[1])
                queue.task_done()
            else:
                logger.debug(f'Sleeping 2 sec')
                time.sleep(2)
    except Exception as e:
        logger.error("Error in the processing worker")
        logger.exception(e)
    except KeyboardInterrupt as e:
        logger.info('SIGINT recieved by the processing worker')


def process_square_image(square, grid, microscope_id):
    # square = SquareModel.objects.get(pk=square)
    # grid = AutoloaderGrid.objects.get(pk=grid)
    protocol = load_protocol(os.path.join(grid.directory, 'protocol.yaml'))
    plugins = load_plugins()
    params = grid.params_id
    is_bis = params.bis_max_distance > 0
    if square.status == 'acquired':
        montage = get_file_and_process(square, 'square', directory=microscope_id.scope_path)
        montage.find_targets(load_protocol()['holeFinders'])
        targets = montage.create_targets()
        holes = add_targets(grid, square, targets, HoleModel)

        square = update(square, status='processed', shape_x=montage.shape_x,
                        shape_y=montage.shape_y, pixel_size=montage.pixel_size, refresh_from_db=True)
        transaction.on_commit(lambda: logger.debug('targets added'))
    if square.status == 'processed':
        selector_wrapper(protocol[f'{square.targets_prefix}Selectors'], square, n_groups=5)
        square = update(square, status='selected')
    if square.status == 'selected':
        if is_bis:
            holes = list(HoleModel.objects.filter(square_id=square.square_id))
            holes = group_holes_for_BIS([h for h in holes if h.is_good(plugins=plugins) and not h.is_excluded(protocol, square.targets_prefix)[0]],
                                        max_radius=grid.params_id.bis_max_distance, min_group_size=grid.params_id.min_bis_group_size)
            with transaction.atomic():
                for hole in holes:
                    hole.save()
        logger.info(f'Picking holes on {square}')

        select_n_areas(square, grid.params_id.holes_per_square, is_bis=is_bis)
        square = update(square, status='targets_picked')
    if square.status == 'targets_picked':
        # plot_square(square)
        square = update(square, status='completed', completion_time=timezone.now())
    if square.status == 'completed':
        logger.info(f'Square {square.name} analysis is complete')


def process_hole_image(hole, microscope_id):
    # hole = HoleModel.objects.get(pk=hole)
    montage = get_file_and_process(hole, 'hole', directory=microscope_id.scope_path)
    update(hole, status='processed',
           pixel_size=montage.pixel_size,)


def process_hm_image(hm, microscope_id):
    # hm = HighMagModel.objects.get(pk=hm)
    # microscope = Microscope.objects.get(pk=microscope_id)
    logger.info(f'Processing {hm}, {hm.pk}, {hm.status}')
    if hm.status == 'acquired':
        if hm.frames is not None:
            frames_dir = os.path.join(microscope_id.scope_path, 'movies')
            montage = High_Mag(**hm.__dict__)
            is_metadata = montage.create_dirs(force_reproces=False)
            if not is_metadata:
                try:
                    montage.parse_mdoc(file=os.path.join(frames_dir, hm.frames), movie=True)
                except Exception as e:
                    logger.info('waiting for mdoc file')
                    time.sleep(2)
                    montage.parse_mdoc(file=os.path.join(frames_dir, hm.frames), movie=True)
                montage.align_frames(frames_dir=frames_dir)
                montage.build_montage(raw_only=False)
                save_image(montage.montage, montage._id, extension='png')
                montage.save_metadata()
        else:
            montage = get_file_and_process(hm, 'high_mag', directory=microscope_id.scope_path)
        hm = update(hm, pixel_size=montage.pixel_size, status='processed')
    else:
        montage = High_Mag(**hm.__dict__)
        is_metadata = montage.create_dirs(force_reproces=False)

    if hm.status == 'processed':
        montage.CTFfind(microscope_id)
        hm = update(hm,
                    defocus=montage.defocus,
                    astig=montage.astig,
                    ctffit=montage.ctffit,
                    angast=montage.angast,
                    status='completed', refresh_from_db=True)
        update(hm.hole_id, status='completed', completion_time=timezone.now())
    # grid = update(grid, last_update=None)


def write_sessionLock(session, lockFile):
    with open(lockFile, 'w') as f:
        f.write(session.session_id)


def autoscreen(session_id):
    # cache.clear()
    session = ScreeningSession.objects.get(session_id=session_id)
    microscope = session.microscope_id
    lockFile, sessionLock = session.isScopeLocked
    add_log_handlers(directory=session.directory, name='run.out')
    logger.debug(f'Main Log handlers:{logger.handlers}')
    is_stop_file()
    # SETUP SESSION LOGGING
    # logger = create_logger('autoscreen', os.path.join(session.directory, 'run.out'))
    # create_logger('processing', os.path.join(session.directory, 'proc.out'))
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
        if microscope.serialem_IP == 'xxx.xxx.xxx.xxx':
            logger.info('Setting scope into test mode')
            scopeInterface = FakeScopeInterface
        else:
            scopeInterface = SerialemInterface
        with scopeInterface(ip=microscope.serialem_IP,
                            port=microscope.serialem_PORT,
                            energyfilter=session.detector_id.energy_filter,
                            directory=microscope.windows_path,
                            scope_path=microscope.scope_path) as scope:
            # START image processing processes
            processing_queue = multiprocessing.JoinableQueue()
            child_process = multiprocessing.Process(target=processing_worker_wrapper, args=(session.directory, processing_queue,))
            child_process.start()
            logger.debug(f'Main Log handlers:{logger.handlers}')
            for grid in grids:
                status = run_grid(grid, session, processing_queue, scope)
                if status == 'stop':
                    raise KeyboardInterrupt
            status = 'complete'
    except Exception as e:
        logger.exception(e)
        status = 'error'
    except KeyboardInterrupt:
        logger.info('Stopping Smartscope.py autoscreen')
        status = 'killed'
    finally:
        # SerialEM.disconnect()
        os.remove(lockFile)
        update(process, status=status)
        logger.debug('Wrapping up')
        processing_queue.put('exit')
        child_process.join()
        logger.debug('Process joined')
        os.killpg(0, signal.SIGINT)  # Make sure child processes are killed, testing this.
