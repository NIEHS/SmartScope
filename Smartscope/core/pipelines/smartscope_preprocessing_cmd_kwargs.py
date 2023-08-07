
from typing import Union
from pathlib import Path
from pydantic import BaseModel, Field, validator
import logging
logger = logging.getLogger(__name__)


class SmartScopePreprocessingCmdKwargs(BaseModel):
    n_processes:int = 1
    frames_directory:Union[Path,None] = None

    @validator('frames_directory')
    def is_frame_directory_empty(cls,v):
        logger.debug(f'{v}, {type(v)}')
        if v == '' or v == Path('.'):
            return None
        return v
