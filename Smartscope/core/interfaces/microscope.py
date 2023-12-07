from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass
class MicroscopeState:
    defocusTarget: float = 0
    currentDefocus: float = 0
    imageShiftX: float = 0
    imageShiftY: float = 0
    stageX: float = 0
    stageY: float = 0
    stageZ: float = 0
    tiltAngle: float = None
    preAFISimageShiftX: float = 0
    preAFISimageShiftY: float = 0

    def setStage(self,stageX,stageY,stageZ):
        self.stageX = stageX
        self.stageY = stageY
        self.stageZ = stageZ
    
    def getStage(self):
        return self.stageX, self.stageY, self.stageZ

    def reset_image_shift_values(self):
        self.imageShiftX = 0
        self.imageShiftY = 0

class AtlasSettings(BaseModel):
    mag:int = Field(alias='atlas_mag')
    maxX:int = Field(alias='atlas_max_tiles_X')
    maxY:int = Field(alias='atlas_max_tiles_Y')
    spotSize:int = Field(alias='spot_size')
    c2:float = Field(alias='c2_perc')
    atlas_to_search_offset_x:float
    atlas_to_search_offset_y:float
    atlas_c2_aperture: Optional[int] = None

    class Config:
        from_attributes=True

class Detector(BaseModel):
    energyFilter:bool = Field(alias='energy_filter')
    framesDir:str = Field(alias='frames_windows_directory')

    class Config:
        from_attributes=True

class Microscope(BaseModel):
    loaderSize:int = Field(alias='loader_size')
    ip:str = Field(alias='serialem_IP')
    port:int = Field(alias='serialem_PORT')
    directory:str= Field(alias='windows_path')
    scopePath:str = Field(alias='scope_path')
    apertureControl:bool = Field(alias='aperture_control', default=False)
    coldFEG:bool = Field(alias='cold_FEG', default=False)

    class Config:
        from_attributes=True

class CartridgeLoadingError(Exception):
    pass

