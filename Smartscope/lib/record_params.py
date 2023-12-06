'''
'''

import numpy as np
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

 
class RecordParams(BaseModel):
    detector_size_x:int
    detector_size_y:int
    pixel_size:float
    beam_size:int
    hole_size:float

    @property
    def detector_size(self):
        return np.array([self.detector_size_x,self.detector_size_y])

    @property
    def pixel_size_um(self):
        return self.pixel_size / 10_000
    
    @property
    def detector_size_um(self):
        return self.detector_size * self.pixel_size_um
    
    @property
    def beam_size_um(self):
        return self.beam_size / 1_000