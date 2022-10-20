from abc import ABC, abstractmethod
from functools import partial
import signal
import time
from typing import List
from Smartscope.core.db_manipulations import websocket_update
from Smartscope.core.models import AutoloaderGrid
from pathlib import Path
from Smartscope.lib.preprocessing_methods import get_CTFFIN4_data, process_hm_from_average, process_hm_from_frames, processing_worker_wrapper
from Smartscope.core.models.models_actions import update_fields
import os
import sys
import multiprocessing
import logging
from django.db import transaction


logger = logging.getLogger(__name__)


class PreprocessingPipeline(ABC):

    def __init__(self, grid: AutoloaderGrid):
        self.grid = grid
        self.directory = grid.directory

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def list_incomplete_processes(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    def update_processes(self):
        to_update = []
        for instance in self.incomplete_processes:
            is_updated, instance = self.check_for_update(instance)
            to_update.append(instance)

    @abstractmethod
    def check_for_update(self, instance):
        pass


class SmartscopePreprocessingPipeline(PreprocessingPipeline):

    to_process_queue = multiprocessing.JoinableQueue()
    processed_queue = multiprocessing.Queue()
    child_process = []
    to_update = []
    incomplete_processes = []

    def __init__(self, grid: AutoloaderGrid, frames_directory=None):
        super().__init__(grid=grid)
        self.microscope = self.grid.session_id.microscope_id
        self.detector = self.grid.session_id.detector_id
        self.frames_directory = [Path(self.detector.frames_directory)]

        if frames_directory is not None:
            self.frames_directory.append(frames_directory)

    def start(self, n_processes: int = 1):
        os.chdir(self.grid.directory)
        session = self.grid.session_id
        for n in range(int(n_processes)):
            proc = multiprocessing.Process(target=processing_worker_wrapper, args=(
                session.directory, self.to_process_queue,), kwargs={'output_queue': self.processed_queue})
            proc.start()
            self.child_process.append(proc)
        self.list_incomplete_processes()
        while True:
            self.queue_incomplete_processes()
            self.to_process_queue.join()
            self.check_for_update()
            self.update_processes()
            self.list_incomplete_processes()
            self.grid.refresh_from_db()
            if self.grid.status == 'complete' and len(self.incomplete_processes) == 0:
                break

    def list_incomplete_processes(self):
        self.incomplete_processes = list(self.grid.highmagmodel_set.exclude(
            status__in=['queued', 'started', 'completed']).order_by('completion_time')[:20])

    def queue_incomplete_processes(self):
        from_average = partial(process_hm_from_average, scope_path_directory=self.microscope.scope_path,
                               spherical_abberation=self.microscope.spherical_abberation)
        from_frames = partial(process_hm_from_frames, frames_directories=self.frames_directory,
                              spherical_abberation=self.microscope.spherical_abberation)
        for obj in self.incomplete_processes:
            if obj.frames is None or self.detector.detector_model not in ['K2', 'K3'] or self.grid.params.force_process_from_average:
                self.to_process_queue.put([from_average, [], dict(raw=obj.raw, name=obj.name)])
            else:
                self.to_process_queue.put([from_frames, [], dict(name=obj.name, frames_file_name=obj.frames)])

    def stop(self):
        for proc in self.child_process:
            self.to_process_queue.put('exit')
            proc.join()
        logger.debug('Process joined')

    def check_for_update(self):
        while self.processed_queue.qsize() > 0:
            movie = self.processed_queue.get()
            if not movie.check_metadata():
                continue
            data = get_CTFFIN4_data(movie.ctf)
            data['status'] = 'completed'
            movie.read_image()
            data['shape_x'] = movie.shape_x
            data['shape_y'] = movie.shape_y
            logger.debug(f'Updating {movie.name}')
            instance = [obj for obj in self.incomplete_processes if obj.name == movie.name][0]
            parent = instance.hole_id
            self.to_update += [update_fields(instance, data), update_fields(parent, dict(status='completed'))]

    def update_processes(self):
        logger.info(f'Updating {len(self.to_update)} items in the database')
        if len(self.to_update) == 0:
            logger.info(f'No items to update, waiting 30 seconds before checking again.')
            return time.sleep(30)
        with transaction.atomic():
            [obj.save() for obj in self.to_update]
        websocket_update(self.to_update, self.grid.grid_id)
        self.to_update = []


PREPROCESSING_PIPELINE_FACTORY = dict(smartscopePipeline=SmartscopePreprocessingPipeline)


def highmag_processing(pipeline: PreprocessingPipeline, grid_id: str, n_processes: int = 1) -> None:
    try:
        grid = AutoloaderGrid.objects.get(grid_id=grid_id)
        pipeline = PREPROCESSING_PIPELINE_FACTORY[pipeline](grid)
        pipeline.start(n_processes)

    except Exception as e:
        logger.exception(e)
    except KeyboardInterrupt as e:
        logger.exception(e)
    finally:
        logger.debug('Wrapping up')
        pipeline.stop()
