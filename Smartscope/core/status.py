import os
import logging
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

class status:
    """
    ENUMS don't play well with Django. This is an attempt at creating something equivalent that works
    """

    NULL=None
    STARTED='started'
    QUEUED='queued'
    ACQUIRED='acquired'
    PROCESSED='processed'
    TARGETS_PICKED='targets_picked'
    TARGETS_SELECTED='selected'
    ERROR='error'
    SKIPPED='skipped'
    COMPLETED='completed'



class FileSignal:

    def __init__(self, path:os.PathLike):
        if not isinstance(path,Path):
            self._path = Path(path)
            return
        self._path = path

    @property
    def exists(self):
        return self._path.exists
    
    def create(self):
        return self._path.touch()

    def remove(self):
        return self._path.unlink()

    
    # @property
    # def is_paused(self):
    #     return self.paused_file.exists()
    

    
    # @property
    # def is_stop_file(self):
    #     if not self.stop_file.exists():
    #         return False
    #     logger.debug(f'Stop file {self.stop_file} found.')
    #     self.stop_file.unlink()
    #     raise KeyboardInterrupt()

@dataclass
class FileSignals:

    microscope_id:str
    session_id:str
    grid_id:str

    @property
    def paused_file(self) -> FileSignal:
        return FileSignal(Path(os.getenv('TEMPDIR'), f'paused_{self.microscope_id}'))

    @property
    def stop_file(self) -> FileSignal:
        return Path(os.getenv('TEMPDIR'), f'{self.session_id}.stop')
    
    @property
    def session_lock(self) -> FileSignal:
        return Path()