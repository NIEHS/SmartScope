'''
used by class Montage
'''
from typing import List, Union
import numpy as np
from torch import Tensor

from .process_image import ProcessImage


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

    def flip_y(self, coords, shape_y):
        return np.array([coords[0],shape_y - coords[1]])

    def convert_image_coords_to_stage(self, montage):
        tile, dist = ProcessImage.closest_node(
            self.coords.reshape(-1,2),
            montage.metadata.piece_center
        )
        if 'ImageToStageMatrix' in montage.metadata:
            print('Using ImageToStageMatrix')
            self.stage_x, self.stage_y = ProcessImage.pixel_to_stage_from_vectors(
                self.flip_y(self.coords,montage.shape_y),
                montage.metadata.iloc[tile].ImageToStageMatrix
            )
            self.stage_z = montage.stage_z
            return 
        
        self.stage_x, self.stage_y = ProcessImage.pixel_to_stage(
            dist,
            montage.metadata.iloc[tile],
            montage.metadata.iloc[tile].TiltAngle
        )
        self.stage_z = montage.stage_z
