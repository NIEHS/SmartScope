from dataclasses import dataclass
import serialem as sem
from abc import ABC, abstractmethod
from typing import Any

from Smartscope.lib.montage import Montage


@dataclass
class MicroscopeState:
    defocusTarget: float = 0
    currentDefocus: float = 0
    imageShiftX: float = 0
    imageShiftY: float = 0
    stageX: float = 0
    stageY: float = 0
    stageZ: float = 0
    tiltAngle: float = 0

    def reset_image_shift_values(self):
        self.imageShiftX = 0
        self.imageShiftY = 0


@dataclass
class MicroscopeInterface(ABC):
    ip: str
    port: int
    directory: str
    frames_directory: str
    scope_path: str
    energyfilter: bool
    state: MicroscopeState = MicroscopeState()
    imageHandler: Any = Montage
    loader_size: int = 12
    detector_type: str = 'K2'

    def __enter__(self):
        self.connect(self.directory)
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

    def rollDefocus(self, def1, def2, step):
        mindef = max([def1, def2])
        maxdef = min([def1, def2])
        defocusTarget = round(sem.ReportTargetDefocus() - abs(step), 2)
        if defocusTarget < maxdef or defocusTarget > mindef:
            defocusTarget = mindef
        self.state.defocusTarget = defocusTarget

    @abstractmethod
    def eucentricHeight(self, tiltTo=10, increments=-5) -> float:
        pass

    @abstractmethod
    def atlas(self, mag, c2, spotsize, tileX, tileY, file='', center_stage_x=0, center_stage_y=0):
        pass

    @abstractmethod
    def square(self, stageX, stageY, stageZ, file=''):
        pass

    @abstractmethod
    def align():
        pass

    @abstractmethod
    def lowmagHole(self, stageX, stageY, stageZ, tiltAngle, file='', is_negativestain=False, aliThreshold=500):
        pass

    @abstractmethod
    def focusDrift(self, def1, def2, step, drifTarget):
        pass

    @abstractmethod
    def highmag(self, isXi, isYi, isX, isY, currentDefocus, tiltAngle, file='', frames=True):
        pass

    @abstractmethod
    def connect(self, directory: str):
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
