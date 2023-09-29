
import os
import sys
from django.conf import settings
# import multiprocessing
import logging

logger = logging.getLogger(__name__)


from .interfaces.microscope import Microscope, Detector, AtlasSettings
from .interfaces.microscope_methods import select_microscope_interface
from Smartscope.core.models import ScreeningSession, Process
from Smartscope.core.status import status
from .grid.grid_status import GridStatus
from Smartscope.core.db_manipulations import update

from Smartscope.lib.preprocessing_methods import processing_worker_wrapper
from Smartscope.lib.logger import add_log_handlers

from .run_grid import run_grid, is_stop_file


def autoscreen(session_id:str):
    '''
    major procedure: autoscreen
    '''
    session = ScreeningSession.objects.get(session_id=session_id)
    microscope = session.microscope_id
    # lockFile, sessionLock = session.isScopeLocked
    add_log_handlers(directory=session.directory, name='run.out')
    logger.debug(f'Main Log handlers:{logger.handlers}')
    process = create_process(session)
    is_stop_file(session.session_id)
    if microscope.isLocked:
        logger.warning(f"""
            The requested microscope is busy.
            Lock file {microscope.lockFile} found
            Session id: {session} is currently running.
            If you are sure that the microscope is not running,
            remove the lock file and restart.
            Exiting.
        """)
        sys.exit(0)
    write_sessionLock(session, microscope.lockFile)

    try:
        grids = list(session.autoloadergrid_set.all().order_by('position'))
        logger.info(f'Process: {process}')
        logger.info(f'Session: {session}')
        logger.info(f"Grids: {', '.join([grid.__str__() for grid in grids])}")
        scopeInterface = select_microscope_interface(microscope)

        with scopeInterface(
                microscope = Microscope.model_validate(session.microscope_id),
                detector= Detector.model_validate(session.detector_id) ,
                atlas_settings= AtlasSettings.model_validate(session.detector_id)
            ) as scope:
            # START image processing processes
            # processing_queue = multiprocessing.JoinableQueue()
            # child_process = multiprocessing.Process(
            #     target=processing_worker_wrapper,
            #     args=(session.directory, processing_queue,)
            # )
            # child_process.start()
            logger.debug(f'Main Log handlers:{logger.handlers}')

            # RUN grid
            for grid in grids:
                status = run_grid(grid, session,  scope) #processing_queue,
            status = 'complete'
    except Exception as e:
        logger.exception(e)
        status = 'error'
        if grid in locals():
            update.grid = grid
            update(grid, status=GridStatus.ERROR)
    except KeyboardInterrupt:
        logger.info('Stopping Smartscope.py autoscreen')
        status = 'killed'
    finally:
        os.remove(microscope.lockFile)
        update(process, status=status)
        logger.debug('Wrapping up')
        # processing_queue.put('exit')
        # child_process.join()
        # logger.debug('Process joined')



def create_process(session):
    process = session.process_set.first()

    if process is None:
        process = Process(session_id=session, PID=os.getpid(), status='running')
        process = process.save()
        return process

    return update(process, PID=os.getpid(), status='running')


def write_sessionLock(session, lockFile):
    with open(lockFile, 'w') as f:
        f.write(session.session_id)