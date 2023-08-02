from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Union
import mrcfile
import os
import numpy as np
import pandas as pd

from .temporary_s3_file import TemporaryS3File

import logging
logger = logging.getLogger(__name__)

@dataclass
class BaseImage(ABC):

    name: str
    working_dir: str = ''
    is_movie: bool = False
    metadata: Union[pd.DataFrame, None] = None
    _raw = None
    _mdoc = None
    _shape_x = None
    _shape_y = None
    _image = None

    def __post_init__(self):
        '''
        auto called after initialization
        '''
        self._directory = Path(self.working_dir, self.name)
        self._image_path = Path(self._directory, f'{self.name}.mrc')
        self._metadataFile = Path(self._directory, f'{self.name}_metadata.pkl')

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, value):
        self._directory = value

    @property
    def image_path(self):
        return self._image_path

    @image_path.setter
    def image_path(self, value):
        self._image_path = value

    @property
    def metadataFile(self):
        return self._metadataFile

    @metadataFile.setter
    def metadataFile(self, value):
        self._metadataFile = value

    @property
    def image(self):
        if self._image is not None:
            return self._image
        raise AttributeError('''
            Image is not loaded. Ensure that the image is loaded
            by using the BaseImage.read_image() or Montage.
            build_montage() method first
        ''')

    @property
    def png(self):
        return Path(self.working_dir, 'pngs', f'{self.name}.png')

    @property
    def raw(self):
        '''
        *.mrc in raw/
        '''
        if self._raw is not None:
            return self._raw
        return Path(self.working_dir, 'raw', f'{self.name}.mrc')
    
    @raw.setter
    def raw(self, value):
        self._raw = value 
        self._mdoc = Path(str(value) + '.mdoc')

    @property
    def mdoc(self):
        '''
        get path of *.mdoc one of raw data
        default: all raw data are stored in raw/
        '''
        if self._mdoc is not None and os.path.isfile(self._mdoc):
            return self._mdoc
        mdoc = Path(self.working_dir, 'raw', f'{self.name}.mrc.mdoc')
        if os.path.isfile(mdoc):
            return mdoc
        mdoc = Path(self.working_dir, f'{self.name}.mrc.mdoc')
        if os.path.isfile(mdoc):
            return mdoc
        return None

    @property
    def ctf(self):
        return Path(self.directory, 'ctf.txt')        

    def set_shape_from_image(self):
        self._shape_x = self.image.shape[0]
        self._shape_y = self.image.shape[1]

    @property
    def shape_x(self):
        if self._shape_x is not None:
            return self._shape_x
        return self.image.shape[0]

    @property
    def shape_y(self):
        if self._shape_y is not None:
            return self._shape_y
        return self.image.shape[1]
    
    @property
    def center(self):
        return np.array([self.shape_y/2, self.shape_x//2],dtype=int)

    def get_tile(self, tileIndex=0):
        return self.metadata.iloc[tileIndex]

    @property
    def rotation_angle(self):
        return self.metadata.iloc[0].RotationAngle

    @property
    def stage_z(self):
        return self.metadata.iloc[0].StageZ

    @property
    def pixel_size(self):
        return self.metadata.iloc[0].PixelSpacing


    def read_data(self):
        '''
        load data after initialization
        '''
        self.read_image()
        self.read_metadata()

    def check_metadata(self, check_AWS=False):
        if self.image_path.exists() and self.metadataFile.exists():
            logger.info('Found metadata, reading...')
            self.read_data()
            return True

        if check_AWS:
            logger.debug(f'{self.image_path}, {self.metadataFile}')
            with TemporaryS3File([self.image_path, self.metadataFile]) as temp:
                self.image_path, self.metadataFile = temp.temporary_files
                self.read_data()
            return True
        return False
    
    def read_image(self, force=False):
        '''
        read *.mrc
        '''
        if self._image is not None:
            return
        try:
            with mrcfile.open(self.image_path) as mrc:
                self._image = mrc.data
        except FileNotFoundError:
            with mrcfile.open(self.raw) as mrc:
                self._image = mrc.data
        return

    def read_metadata(self):
        '''
        read *.pkl
        '''
        self.metadata = pd.read_pickle(self.metadataFile)

    def save_metadata(self):
        self.metadata.to_pickle(self.metadataFile)

    def make_symlink(self):
        relative = os.path.relpath(self.raw,self.directory)
        if self.image_path.exists():
            return
        logger.debug(f'Relative path from {self.directory} to raw = {relative}')
        os.symlink(relative, self.image_path)


    # import imutils
    # def downsample(self, scale=2) -> np.ndarray:
    #     return imutils.resize(self.image, height=int(self.shape_x // scale))

    # @property
    # def image_center(self):
    #     return np.array([self.shape_x, self.shape_y]) // 2

