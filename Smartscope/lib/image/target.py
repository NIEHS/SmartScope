'''
used by class Montage
'''
from typing import List, Union
import numpy as np
from torch import Tensor

from .process_image import ProcessImage
# from .montage import Montage
import logging

logger = logging.getLogger(__name__)


class Target:

    _x: Union[int,None] = None
    _y: Union[int,None] = None
    shape: Union[list, Tensor]
    quality: Union[str, None] = None
    area: Union[float, None] = None
    radius: Union[float, None] = None
    stage_x: Union[float, None] = None
    stage_y: Union[float, None] = None
    stage_z: Union[float, None] = None

    def __init__(self,
        shape: Union[list, np.array],
        quality: Union[str,None]=None,
        from_center=False
    ) -> None:
        self.quality = quality
        if from_center:
            self.x = shape[0]
            self.y = shape[1]
            return
        self.shape = shape
        self.x = None
        self.y = None

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value = None):
        if isinstance(value,list):
            self._x = int(value[0] + (value[2] - value[0]) // 2)
            return 
        if value is None:
            self._x = int(self.shape[0] + (self.shape[2] - self.shape[0]) // 2)
            return
        self._x = value    

    @property
    def y(self):
        return self._y
    
    @property
    def coords(self):
        return np.array([self._x,self._y])
    

    @property
    def stage_coords(self):
        return np.array([self.stage_x,self.stage_y])

    @y.setter
    def y(self, value = None):
        if isinstance(value,list):
            self._y = int(value[1] + (value[3] - value[1]) // 2)
            return
        if value is None:
            self._y = int(self.shape[1] + (self.shape[3] - self.shape[1]) // 2) 
            return
        self._y = value

    def set_area_radius(self, shape_type):

        len1 = int(self.shape[2] - self.shape[0])
        len2 = int(self.shape[3] - self.shape[1])

        # if shape_type == 'square':
        self.area = len1 * len2
            # return

        # if shape_type == 'hole':

        self.radius = min(len1, len2) / 2
            # self.area = np.pi * (self.radius ** 2)

    @staticmethod
    def flip_y(coords, shape_y):
        flipped_coords= np.array([coords[0],shape_y - coords[1]])
        logger.debug(f'Flipping y coords: {coords} to {flipped_coords}')
        return flipped_coords
    


    def convert_image_coords_to_stage(self, montage, force_legacy=False, compare=False):
        tile, dist = ProcessImage.closest_node(
            self.coords.reshape(-1,2),
            montage.metadata.piece_center
        )
        print(montage.metadata.columns)
        if 'ImageToStageMatrix' in montage.metadata.iloc[-1].keys() and not force_legacy:
            logger.debug(f'Montage shape_x: {montage.shape_x}, and shape_y: {montage.shape_y}.')
            flipped_coords = self.flip_y(self.coords,montage.shape_x)
            self.stage_x, self.stage_y = ProcessImage.pixel_to_stage_from_vectors(
                flipped_coords,
                montage.metadata.iloc[-1].ImageToStageMatrix
            )
            # logger.info(f'\nUsed ImageToStageMatrix vectors {montage.metadata.iloc[-1].ImageToStageMatrix} to convert:\n\tY-flipped image coords: {flipped_coords} to\n\tStage coords: {self.stage_coords}')
            self.stage_z = montage.stage_z
            if not compare:
                return
            is_to_stage = np.array([self.stage_x, self.stage_y])
        
        (self.stage_x, self.stage_y), vector = ProcessImage.pixel_to_stage(
            dist,
            montage.metadata.iloc[tile],
            montage.metadata.iloc[tile].TiltAngle,
            return_vector=True
        )
        # logger.info(f'\nUsed mdoc-derived vector {vector.tolist()} to convert:\n\tImage coords: {self.coords} to\n\tStage coords: {self.stage_coords}')
        self.stage_z = montage.stage_z
        mdoc_to_stage = np.array([self.stage_x, self.stage_y])
        if compare:
            difference = is_to_stage - mdoc_to_stage
            logger.info(f'Difference between ImageToStageMatrix and mdoc-derived vectors: {difference} microns')
            return is_to_stage, mdoc_to_stage, difference
