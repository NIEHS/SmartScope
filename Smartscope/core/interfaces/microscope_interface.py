from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

import serialem as sem
from .microscope import MicroscopeState, AtlasSettings, Detector, Microscope

logger = logging.getLogger(__name__)


@dataclass
class MicroscopeInterface(ABC):
    microscope: Microscope
    detector: Detector
    atlas_settings:AtlasSettings
    state: MicroscopeState = MicroscopeState()
    has_hole_ref: bool = False
    hole_crop_size: int = 0
    focus_position_set: bool = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def reset_image_shift_values(self):
        self.state.reset_image_shift_values()

    @abstractmethod
    def checkDewars(self, wait=30) -> None:
        pass

    @abstractmethod
    def checkPump(self, wait=30):
        pass

    def flash_cold_FEG(self, ffDelay:int):
        pass

    def rollDefocus(self, def1, def2, step):
        mindef = max([def1, def2])
        maxdef = min([def1, def2])
        defocusTarget = round(sem.ReportTargetDefocus() - abs(step), 2)
        if defocusTarget < maxdef or defocusTarget > mindef:
            defocusTarget = mindef
        self.state.defocusTarget = defocusTarget

    def reset_state(self):
        self.has_hole_ref = False
        self.focus_position_set = False

    
    @abstractmethod
    def report_stage(self):
        return 0,0,0

    @abstractmethod
    def eucentricHeight(self, tiltTo:int=10, increments:int=-5) -> float:
        pass

    @abstractmethod
    def eucentricity():
        pass

    @abstractmethod
    def get_image_settings(self, *args, **kwargs):
        pass

    @abstractmethod
    def buffer_to_numpy():
        pass

    @abstractmethod
    def numpy_to_buffer():
        pass

    @abstractmethod
    def set_atlas_optics(self):
        pass

    @abstractmethod
    def atlas(self, mag, c2, spotsize, tileX, tileY, file='', center_stage_x=0, center_stage_y=0):
        pass

    @abstractmethod
    def realign_to_square(self):
        return 0,0,0

    @abstractmethod
    def square(self, file=''):
        pass

    @abstractmethod
    def align_to_hole_ref(self):
        return 0,0 

    @abstractmethod
    def reset_image_shift(self):
        pass

    @abstractmethod
    def align_to_coord(self, coord):
        pass

    @abstractmethod
    def moveStage(self, stage_x, stage_y, stage_z):
        pass

    @abstractmethod
    def acquire_medium_mag(self):
        pass


    @abstractmethod
    def medium_mag_hole(self, tiltAngle, file=''):
        pass

    @abstractmethod
    def focusDrift(self, def1, def2, step, drifTarget):
        pass

    @abstractmethod
    def load_hole_ref(self):
        pass

    @abstractmethod
    def image_shift_by_microns(self,isX,isY,tiltAngle, afis:bool=False):
        pass

    @abstractmethod
    def highmag(self, isXi, isYi, isX, isY, currentDefocus, tiltAngle, file='', frames=True):
        pass

    @abstractmethod
    def connect(self, directory: str):
        pass

    @abstractmethod
    def setFocusPosition(self, distance, angle):
        pass

    @abstractmethod
    def setup(self, saveframes, zerolossDelay):
        pass

    @abstractmethod
    def disconnect(self, close_valves=True):
        pass

    @abstractmethod
    def loadGrid(self, position):
        pass

    def refineZLP(self, zerolossDelay):
        pass

    def collectHardwareDark(self, harwareDarkDelay:int):
        pass
    
    def reset_AFIS_image_shift(self, afis:bool=False):
        pass


