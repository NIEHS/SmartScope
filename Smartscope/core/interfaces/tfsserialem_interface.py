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
    CONDENSER:int=1
    CONDENSER_3:int=3
    OBJECTIVE:int = 2

class TFSSerialemInterface(SerialemInterface):
    apertures: Apertures = TFSApertures

    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)
        self.apertures = TFSApertures

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            self.logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    def checkPump(self, wait=30):
        while True:
            if sem.IsPVPRunning() == 0:
                return
            self.logger.info(f'Pump is Running, waiting {wait}s')
            time.sleep(wait)

    def atlas(self, size, file=''):
        super().atlas(size, file)
        sem.SetLowDoseMode(1)
