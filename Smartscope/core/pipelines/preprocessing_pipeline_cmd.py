import time
from typing import Optional, Any
import psutil
import subprocess as sub
import shlex
from pathlib import Path
from pydantic import BaseModel, Field


from Smartscope.core.models.grid import AutoloaderGrid
from Smartscope.lib.Datatypes.models import generate_unique_id

import logging
logger = logging.getLogger(__name__)

class PreprocessingPipelineCmd(BaseModel):
    pipeline:str
    cache_id:str = Field(default_factory=generate_unique_id)
    process_pid: Optional[int] = None
    kwargs: Any

    def is_running(self):
        if self.process_pid is None:
            return False
        try:
            process = psutil.Process(self.process_pid)
            if process.is_running():
                return True
            else:
                return False
        except psutil.NoSuchProcess:
            return False

    def stop(self, grid:AutoloaderGrid):
        stop_file = Path(grid.directory,'preprocessing.stop')
        stop_file.touch()
        while self.is_running():
            try:
                process = psutil.Process(self.process_pid)
            except psutil.NoSuchProcess:
                break
            logger.debug(f'Will check again if process as been killed. '+\
                'This may take a while for all actions to complete.')
            time.sleep(2)
        logger.info('Preprocessing has been killed gracefully.')
    
    def start(self, grid:AutoloaderGrid):
        proc = sub.call(shlex.split(f'smartscope.sh highmag_processing {grid.grid_id}'))
        time.sleep(3)

