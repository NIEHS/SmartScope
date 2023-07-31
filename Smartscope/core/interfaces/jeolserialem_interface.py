import serialem as sem
from typing import Callable
import time
import logging
from .serialem_interface import SerialemInterface

logger = logging.getLogger(__name__)


def remove_condenser_aperture(function: Callable, *args, **kwargs):
    def wrapper(*args, **kwargs):
        sem.RemoveAperture(0)
        function(*args, **kwargs)
        sem.ReInsertAperture(0)
    return wrapper


class JEOLSerialemInterface(SerialemInterface):

    def checkPump(self, wait=30):
        pass

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    @remove_condenser_aperture
    def atlas(self, *args, **kwargs):
        super().atlas(*args,**kwargs)