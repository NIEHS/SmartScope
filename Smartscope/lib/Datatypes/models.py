from abc import ABC
import random
import string
from datetime import datetime
from pathlib import Path
from typing import List, Union, Dict
from pydantic import BaseModel, Field
import numpy as np

def generate_unique_id(extra_inputs=[], N=30):
    if len(extra_inputs) != 0:
        base_id = ''.join(extra_inputs)
    else:
        base_id = ''
    random_id = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(N - len(base_id)))
    return ''.join([base_id, random_id]).replace('.', '_').replace(' ', '_')

class Finder(BaseModel):
    x: int
    y: int
    stage_x: float
    stage_y: float
    stage_z: float
    method_name: str

class Target(BaseModel, ABC):
    name: str
    number: int
    grid_id: str
    pixel_size: Union[float,None] = None
    shape_x: Union[float,None] = None
    shape_y : Union[float,None] = None
    selected:  bool = False
    status: Union[str,None] = None
    completion_time: Union[datetime,None] = None

    finders: List[Finder]
    ## NEED TO ADD CLASSIFIERS AND SELECTORS BUT IT'S GOOD FOR TESTING RIGHT NOW
    class Config:
        allow_population_by_field_name = True
        orm_mode=True

    @property
    def stage_coords(self) -> np.ndarray:
        return np.array([self.finders[0].stage_x, self.finders[0].stage_y])

class HoleModel(Target):
    hole_id : str = Field(alias='id')
    bis_type: str
    radius: int
    area: float
    square_id: str

class HighMagModel(Target):
    hm_id: Union[str,bool] = Field(alias='id',default=False)
    hole_id:str
    is_x: Union[float,None]= None
    is_y: Union[float,None]= None
    offset: float = 0
    frames: Union[str,None] = None
    defocus: Union[float,None]= None
    astig: Union[float,None]= None
    angast: Union[float,None]= None
    ctffit: Union[float,None]= None
    