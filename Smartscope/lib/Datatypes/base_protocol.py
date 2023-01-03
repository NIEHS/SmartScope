from pydantic import BaseModel, Field
from typing import List, Optional

class TargetPlugins(BaseModel):
    finders: List[str] = Field(default_factory=list)
    selectors: List[str] = Field(default_factory=list)

class MagLevel(BaseModel):
    acquisition: List[str]
    targets: Optional[TargetPlugins] = TargetPlugins()

class BaseProtocol(BaseModel):
    name: str
    atlas: MagLevel
    square: MagLevel
    mediumMag: MagLevel
    highMag: MagLevel
    description: str = ''