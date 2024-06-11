import serialem as sem
from typing import Callable, Optional
import functools
import time
import logging
from .serialem_interface import SerialemInterface
from .microscope_interface import Apertures

logger = logging.getLogger(__name__)

class TFSApertures(Apertures):
    CONDENSER_1:int=0
    CONDENSER_2:int=1
    CONDENSER_3:int=3
    OBJECTIVE:int = 2

def change_aperture_temporarily(function: Callable, aperture:Apertures, aperture_size:Optional[int], wait:int=10):
    def wrapper(*args, **kwargs):
        inital_aperture_size = int(sem.ReportApertureSize(aperture))
        if inital_aperture_size == aperture_size or aperture_size is None:
            return function(*args, **kwargs)
        msg = f'Changing condenser aperture {aperture} from {inital_aperture_size} to {aperture_size} and waiting {wait}s.'
        sem.Echo(msg)
        logger.info(msg)
        sem.SetApertureSize(aperture,aperture_size)
        time.sleep(wait)
        function(*args, **kwargs)
        msg = f'Resetting condenser aperture to {inital_aperture_size}.'
        sem.Echo(msg)
        logger.info(msg)
        sem.SetApertureSize(aperture,inital_aperture_size)
    return wrapper    

def remove_objective_aperture(function: Callable, wait:int=10):
    def wrapper(*args, **kwargs):
        msg = 'Removing objective aperture.'
        sem.Echo(msg)
        logger.info(msg)
        sem.RemoveAperture(TFSApertures.OBJECTIVE)
        function(*args, **kwargs)
        msg = f'Reinserting objective aperture and waiting {wait}s.'
        sem.Echo(msg)
        logger.info(msg)
        sem.ReInsertAperture(TFSApertures.OBJECTIVE)
        time.sleep(wait)

    def no_wrap(*args,**kwargs):
        msg = 'Objective aperture already out. Skipping removal and reinstertion.'
        sem.Echo(msg)
        logger.info(msg)
        function(*args, **kwargs)

    if sem.ReportApertureSize(TFSApertures.OBJECTIVE) == 0:
        return no_wrap
    return wrapper

class TFSSerialemInterface(SerialemInterface):
    apertures: Apertures = TFSApertures

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    def checkPump(self, wait=30):
        while True:
            if sem.IsPVPRunning() == 0:
                return
            logger.info(f'Pump is Running, waiting {wait}s')
            time.sleep(wait)

    def atlas(self, size, file=''):
        if self.microscope.apertureControl:
            change_aperture_temporarily(
                function=remove_objective_aperture(super().atlas), 
                aperture=self.apertures.CONDENSER_2,
                aperture_size=self.atlas_settings.atlas_c2_aperture
            )(size,file)
        else:
            super().atlas(size, file)
        sem.SetLowDoseMode(1)
