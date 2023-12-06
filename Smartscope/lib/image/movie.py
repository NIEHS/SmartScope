from dataclasses import dataclass
from pathlib import Path
import os
from typing import List

from .base_image import BaseImage
from .image_file import parse_mdoc

import logging
logger = logging.getLogger(__name__)

@dataclass
class Movie(BaseImage):
    is_movie: bool = True
    frames_directory = ''
    frames_file = ''

    def __post_init__(self):
        '''
        auto called after initialization
        '''
        super().__post_init__()
        self.directory.mkdir(exist_ok=True)

    @property
    def shifts(self):
        return Path(self.directory, 'ali.xf')

    def has_directory(self):
        if self.directory.exists():
            return True
        logger.info(f'{self.directory} does not exists')
        return False


    def metadata_exist(self):
        if self.image_path.exists() and self.shifts.exists() and self.ctf.exists():
            logger.info(f'Movies are already processed. Skipping')
            return True
        return False
    
    def validate_working_dir(self):
        if self.working_dir not in (None, '') and \
            os.path.isdir(self.working_dir):
            return True
        self.working_dir = ''
        return False

    def check_frames(self, 
            frames_directories: List[str],
            frame_file_name: str):
        """
        Locate a file from a list of possible locations
        and return the directory in which it was found
        or None if it couldn't be found
        update self.frames_directory, self.frames_file
        """
        for directory in frames_directories:
            file_path = Path(directory, frame_file_name)
            if file_path.exists():
                self.frames_directory = directory
                self.frames_file = file_path
                return True
        logger.info(f"Frames not found in {frames_directories}. Skipping.")
        return False

    def check_mdoc(self, frames_file_name: str):
        mdoc_file = Path(self.frames_directory, f'{frames_file_name}.mdoc')
        if mdoc_file.exists():
            self.metadata = parse_mdoc(mdocFile=mdoc_file, movie=True)
            if self.metadata is None:
                logger.info(f'Mdoc file not found {mdoc_file}. Skipping.')
                return None
            return mdoc_file
        logger.info(f'Mdoc file {mdoc_file} is not found. Skipping.')
        return None
        