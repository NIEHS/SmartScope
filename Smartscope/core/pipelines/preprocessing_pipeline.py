
from abc import ABC, abstractmethod
from typing import Mapping, Union, Dict, Any
import logging
from pathlib import Path


from Smartscope.core.models.grid import AutoloaderGrid

from django import forms

from .preprocessing_pipeline_cmd import PreprocessingPipelineCmd

logger = logging.getLogger(__name__)

class PreprocessingPipeline(ABC):

    name: str
    verbose_name: str
    description:str
    cmdkwargs_handler: Any
    pipeline_form: forms.Form

    def __init__(self, grid: AutoloaderGrid):
        self.grid = grid
        self.directory = grid.directory

    @classmethod
    def form(cls,data:Union[Mapping,None]=None):
        return cls.pipeline_form(data=data)
    
    @classmethod
    def pipeline_data(cls,data:Dict):
        return PreprocessingPipelineCmd(
            pipeline=cls.name,
            kwargs=cls.cmdkwargs_handler.parse_obj(data)
        ) 
    
    @abstractmethod
    def start(self):
        pass

    def list_incomplete_processes(self):
        self.incomplete_processes = list(
            self.grid.highmagmodel_set.filter(status='acquired').order_by('completion_time')
        )

    @abstractmethod
    def stop(self):
        pass

    def is_stop_file(self):
        stopfile = Path('preprocessing.stop')
        if stopfile.is_file():
            stopfile.unlink()
            return True
        return False

    def update_processes(self):
        to_update = []
        for instance in self.incomplete_processes:
            is_updated, instance = self.check_for_update(instance)
            to_update.append(instance)

    @abstractmethod
    def check_for_update(self, instance):
        pass
    
