import serialem as sem
from typing import Callable
from pydantic import BaseModel
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

class JEOLadditionalSettings(BaseModel):
    transfer_cartridge_path: str = 'C:\Program Data\SerialEM\PyTool\Transfer_Cartridge.bat'

class JEOLSerialemInterface(SerialemInterface):
    additional_settings: JEOLadditionalSettings = JEOLadditionalSettings()
        

    def checkPump(self, wait=30):
        pass

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    def atlas(self, *args, **kwargs):
        if not self.microscope.apertureControl:
            return super().atlas(*args,**kwargs)
        remove_condenser_aperture(
            super().atlas)(*args,**kwargs)
        

    def loadGrid(self, position):
        if self.microscope.loaderSize > 1:
            sem.Delay(5)
            sem.SetColumnOrGunValve(0)
            sem.Delay(5)
            ## HARCODED FOR NOW SINCE THE EXECUTABLE SHOULD BE THERE IN ALL SCOPES
            sem.RunInShell(f"""{self.additional_settings.transfer_cartridge_path} "{position} 3 0" """)
            sem.Delay(5)
        sem.SetColumnOrGunValve(1)

    def flash_cold_FEG(self, ffDelay:int):
        if not self.microscope.coldFEG or ffDelay > 0:
            return
        logger.info('Flashing the cold FEG.')
        sem.LongOperation('FF', ffDelay)
