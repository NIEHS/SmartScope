import serialem as sem

from typing import Callable
from pydantic import BaseModel
import time
import logging
from .serialem_interface import SerialemInterface
from .microscope_interface import Apertures

logger = logging.getLogger(__name__)

def remove_condenser_aperture(function: Callable, aperture, *args, **kwargs):
    def wrapper(*args, **kwargs):
        sem.RemoveAperture(aperture)
        function(*args, **kwargs)
        sem.ReInsertAperture(aperture)
    return wrapper

class JEOLDefaultApertures(Apertures):
    CONDENSER:int=1
    OBJECTIVE:int = 2
    
class JEOLExtraApertures(Apertures):
    CONDENSER:int=0
    CONDENSER_2:int=1
    OBJECTIVE:int = 2
    OBJECTIVE_LOWER:int = 3

class JEOLadditionalSettings(BaseModel):
    transfer_cartridge_path: str = 'C:\Program Data\SerialEM\PyTool\Transfer_Cartridge.bat'

class JEOLSerialemInterface(SerialemInterface):
    additional_settings: JEOLadditionalSettings = JEOLadditionalSettings()
    apertures: Apertures = None
    record_mag: int = 0
        
    def checkPump(self, wait=30):
        pass

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            self.logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    def go_to_highmag(self):
        if self.record_mag == 0:
            raise ValueError('Record mag not set. It should be set in the setup method.')
        sem.SetMag(self.record_mag)
        
    def set_atlas_optics(self):
        return self.set_atlas_optics_imaging_state()

    def atlas(self, *args, **kwargs):
        if self.microscope.apertureControl:
            self.remove_aperture(self.apertures.CONDENSER)
        super().atlas(*args,**kwargs)
        msg = 'Atlas finished, Restoring Search state.'
        self.logger.info(msg)
        sem.RestoreState()

    def square(self, *args, **kwargs):
        if self.microscope.apertureControl:
            self.remove_aperture(self.apertures.CONDENSER)
        super().square(*args,**kwargs)


    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)
        self.apertures = self._apertures_setter()
        sem.SetLowDoseMode(1)
        sem.GoToLowDoseArea('R')
        self.record_mag = int(sem.ReportMag()[0])
        self.logger.info(f'LD highmag parameters found. Record mag: {self.record_mag}')

    def _apertures_setter(self):
        if not self.microscope.apertureControl:
            return None
        extra_apertures_property = self.get_property('JeolHasExtraApertures')
        if extra_apertures_property == 1:
            logging.info('Extra apertures detected')
            return JEOLExtraApertures
        logging.info('Default apertures detected')
        return JEOLDefaultApertures
  
    def loadGrid(self, position):
        if self.microscope.loaderSize > 1:
            sem.Delay(5)
            sem.SetColumnOrGunValve(0)
            sem.Delay(5)
            command = f'{self.additional_settings.transfer_cartridge_path} \"{position} 3 0\"'
            self.logger.info(f'Loading grid with command: \"{command}\"')
            sem.RunInShell(command)
            sem.Delay(5)
        sem.SetColumnOrGunValve(1)

    def flash_cold_FEG(self, ffDelay:int):
        if not self.microscope.coldFEG or ffDelay < 0:
            return
        self.logger.info('Flashing the cold FEG.')
        sem.LongOperation('FF', ffDelay)
