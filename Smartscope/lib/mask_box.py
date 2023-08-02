'''
'''
import cv2
import numpy as np
import logging
logger = logging.getLogger(__name__)


class MaskBox:
    
    def __init__(self,hole_size:float,box_size:int=100,padding_fraction=0.2):
        self.hole_size = hole_size
        self.box_size = box_size
        self.pix_size = (self.hole_size*(1+padding_fraction))/self.box_size
        self.center = np.int8(np.array(self.box().shape) /2)
    
    def box(self):
        return np.zeros([self.box_size]*2)
    
    @property
    def hole_mask(self):
        radius = int(self.hole_size/2//self.pix_size)
        mask = self.box()
        return cv2.circle(mask,self.center,radius,1,cv2.FILLED)