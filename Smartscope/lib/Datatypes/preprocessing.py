from abc import ABC, abstractmethod
from typing import Any, List
from pydantic import BaseModel, Field


class PreprocessingPipelineConfig(BaseModel):
    root_data_directory: str
