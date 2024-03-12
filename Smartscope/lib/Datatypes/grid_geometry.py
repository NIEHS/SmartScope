from typing import Optional, List
from enum import Enum
from pathlib import Path
import json
import logging
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

class GridGeometryLevel(Enum):
    ATLAS = 'square_mesh'
    SQUARE = 'hole_square'
    MEDMAG = 'hole_medmag'

class GridGeometry(BaseModel):
    square_mesh_spacing: Optional[float] = None
    square_mesh_rotation: Optional[float] = None
    hole_square_spacing: Optional[float] = None
    hole_square_rotation: Optional[float] = None
    hole_medmag_spacing: Optional[float] = None
    hole_medmag_rotation: Optional[float] = None

    @classmethod
    def load(cls, directory:str):
        file = Path(directory) / 'grid_geometry.json'
        if not file.exists():
            logging.debug(f'No grid_geometry.json found in {directory}, creating a fresh one.')
            return cls()
        logging.debug(f'Loading geometry from {str(file)}.')
        json_file = json.loads(file.read_text())
        return cls.model_validate(json_file)
    
    def save(self, directory:str):
        file = Path(directory) / 'grid_geometry.json'
        file.write_text(json.dumps(self.model_dump(),indent=4))

    def get_geometry(self, level:GridGeometryLevel):
        spacing = getattr(self, f'{level.value}_spacing')
        rotation = getattr(self, f'{level.value}_rotation')
        if any([spacing is None, rotation is None]):
            logger.warning(f'No {level.value} geometry found.')
        return rotation, spacing
    
    def set_geometry(self, level:GridGeometryLevel, spacing:float, rotation:float):
        setattr(self, f'{level.value}_spacing', spacing)
        setattr(self, f'{level.value}_rotation', rotation)
        logger.info(f'Set {level.value} geometry to spacing: {spacing} and rotation: {rotation}.')