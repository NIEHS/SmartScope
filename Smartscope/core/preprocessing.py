from abc import ABC, abstractmethod
from Smartscope.core.models import AutoloaderGrid, HighMagModel
from pathlib import Path
from Smartscope.lib.preprocessing_methods import get_CTFFIN4_data
from Smartscope.core.models.models_actions import update_fields
import pandas as pd


class PreprocessingPipeline(ABC):

    def __init__(self,grid:AutoloaderGrid):
        self.grid = grid
        self.directory = grid.directory

    @abstractmethod
    def start_pipeline(self):
        pass

    def list_incomplete_processes(self):
        self.incomplete_processes = list(HighMagModel.objects.filter(grid_id=self.grid, status__in=['acquired','processed']))
    
    def update_processes(self):
        to_update = []
        for instance in self.incomplete_processes:
            is_updated, instance = self.check_for_update(instance)
            to_update.append(instance)

    @abstractmethod
    def check_for_update(self, instance):
        pass

class SmartscopePreprocessingPipeline(ABC):

    def check_for_update(self, instance) -> bool, HighMagModel:
        path = Path(self.directory,instance.name,'ctf.txt')
        if not path.exists():
            return False, instance
        data = get_CTFFIN4_data(path)
        return True, update_fields(instance, data)

        


    