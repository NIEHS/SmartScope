
from functools import partial
import time
from typing import Dict, List

import multiprocessing
import logging
from pathlib import Path

from Smartscope.core.db_manipulations import websocket_update
from Smartscope.core.frames import get_frames_prefix, parse_frames_prefix
from Smartscope.core.models.grid import AutoloaderGrid
from Smartscope.lib.preprocessing_methods import get_CTFFIND5_data, \
    process_hm_from_average, process_hm_from_frames, processing_worker_wrapper
from Smartscope.core.models.models_actions import update_fields

from django.db import transaction

from .preprocessing_pipeline import PreprocessingPipeline
from .smartscope_preprocessing_pipeline_form import SmartScopePreprocessingPipelineForm
from .smartscope_preprocessing_cmd_kwargs import SmartScopePreprocessingCmdKwargs

logger = logging.getLogger(__name__)


class SmartscopePreprocessingPipeline(PreprocessingPipeline):

    verbose_name = 'SmartScope Preprocessing Pipeline'
    name = 'smartscopePipeline'
    description = 'Default CPU-based Processing pipeline using IMOD alignframe and CTFFIND4.'
    to_process_queue = multiprocessing.JoinableQueue()
    processed_queue = multiprocessing.Queue()
    child_process: List[multiprocessing.Process] = []
    to_update = []
    incomplete_processes = []
    cmdkwargs_handler = SmartScopePreprocessingCmdKwargs
    pipeline_form= SmartScopePreprocessingPipelineForm

    def __init__(self, grid: AutoloaderGrid, cmd_data:Dict):
        super().__init__(grid=grid)
        self.microscope = self.grid.session_id.microscope_id
        self.detector = self.grid.session_id.detector_id
        self.cmd_data = self.cmdkwargs_handler.parse_obj(cmd_data)
        logger.debug(self.cmd_data)
        self.frames_directory = [Path(self.detector.frames_directory, grid.frames_dir(prefix=parse_frames_prefix(get_frames_prefix(grid),grid)))]
        
        if self.cmd_data.frames_directory is not None:
            self.frames_directory.append(self.cmd_data.frames_directory)
        frames_dirs_str = '\n\t-'.join([str(x) for x in self.frames_directory])
        logger.info(f"Looking for frames in the following directories: {frames_dirs_str}")

    def clear_queue(self):
        while True:
            try:
                self.to_process_queue.get_nowait()
                self.to_process_queue.task_done()
            except multiprocessing.queues.Empty:
                break

    def start_processes(self, n_processes):
        for n in range(int(n_processes)):
            proc = multiprocessing.Process(
                target=processing_worker_wrapper,
                args=(self.grid.directory, self.to_process_queue,),
                kwargs={'output_queue': self.processed_queue}
            )
            proc.start()
            self.child_process.append(proc)


    def start(self):
        # session = self.grid.session_id
        logger.info(f'Starting the preprocessing with {self.cmd_data.n_processes}')
        self.start_processes(self.cmd_data.n_processes)
        self.list_incomplete_processes()
        while not self.is_stop_file():
            self.check_children_processes()
            self.queue_incomplete_processes()
            self.to_process_queue.join()
            self.check_for_update()
            self.update_processes()
            self.list_incomplete_processes()
            self.grid.refresh_from_db()
            if self.grid.status == 'complete' and len(self.incomplete_processes) == 0:
                return

    def list_incomplete_processes(self):
        self.incomplete_processes = list(self.grid.highmagmodel_set\
            .filter(status__in=['acquired','skipped'])\
            .order_by('status','completion_time')[:5*self.cmd_data.n_processes]
        )

    def queue_incomplete_processes(self):
        from_average = partial(
            process_hm_from_average,
            scope_path_directory=self.microscope.scope_path,
            spherical_abberation=self.microscope.spherical_abberation
        )
        from_frames = partial(
            process_hm_from_frames,
            frames_directories=self.frames_directory,
            spherical_abberation=self.microscope.spherical_abberation
        )
        for obj in self.incomplete_processes:
            if obj.frames is None or self.detector.detector_model not in ['K2', 'K3'] \
                or self.grid.params_id.force_process_from_average:
                self.to_process_queue.put(
                    [from_average, [], dict(raw=obj.raw, name=obj.name)]
                )
            else:
                self.to_process_queue.put(
                    [from_frames, [], dict(name=obj.name, frames_file_name=obj.frames)]
                )
    
    def check_children_processes(self):
        logger.info(f'Checking the status of children processes.')
        for proc in self.child_process:
            logger.debug(f'Checking process {proc}')
            proc.join(1)
            logger.debug(f'Process {proc} joined')
            if proc.is_alive():
                logger.debug(f'Child process {proc} is still alive.')
                continue
            logger.error(f'Child process {proc} has died. Restarting it.')
            self.child_process.remove(proc)
            self.start_processes(1)

    def stop(self):
        for proc in self.child_process:
            self.to_process_queue.put('exit')
        for proc in self.child_process:
            proc.join()
        logger.debug('Process joined')

    def check_for_update(self):
        logger.info(f'Checking for updates.')
        while self.processed_queue.qsize() > 0:
            movie = self.processed_queue.get()
            instance = next(filter(lambda x: x.name == movie.name, self.incomplete_processes),None)
            if instance is None:
                logger.error(f'Could not find {movie.name} in {self.incomplete_processes}. Will try again on the next cycle.')
                continue
            data = dict()
            if not movie.check_metadata():
                data['status'] = 'skipped'
                if instance.status != 'skipped':
                    self.to_update.append(update_fields(instance, data))
                continue
            logger.debug(f'Updating {movie.name}')
            try:
                data = get_CTFFIND5_data(movie.ctf)
            except Exception as err:
                logger.exception(err)
                logger.info(f'An error occured while getting CTF data from {movie.name}. Will try again on the next cycle.')
                data['status'] = 'skipped'
                if instance.status != 'skipped':
                    self.to_update.append(update_fields(instance, data))
                continue
            data['status'] = 'completed'
            movie.read_data()
            data['shape_x'] = movie.shape_x
            data['shape_y'] = movie.shape_y
            data['pixel_size'] = movie.pixel_size
            logger.debug(f'Updating {movie.name} with Data: {data}')
            parent = instance.hole_id
            self.to_update += [update_fields(instance, data), update_fields(parent, dict(status='completed'))]

    def update_processes(self):
        logger.info(f'Updating {len(self.to_update)} items in the database')
        if len(self.to_update) == 0:
            sleep_time = 10
            logger.info(f'No items to update, waiting {sleep_time} seconds before checking again.')
            return time.sleep(sleep_time)
        with transaction.atomic():
            for obj in self.to_update:
                obj.save()
            # [obj.save() for obj in self.to_update]
        websocket_update(self.to_update, self.grid.grid_id)
        self.to_update = []

