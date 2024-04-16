import numpy as np
from pathlib import Path
from typing import List, Optional, Callable
import logging
from matplotlib import cm
from matplotlib.colors import rgb2hex
from math import floor, ceil
from pydantic import BaseModel, field_validator

from . import models
from .settings.worker import PLUGINS_FACTORY

logger = logging.getLogger(__name__)


class LagacySorterError(Exception):
    pass

class NotSetError(Exception):
    pass

class SelectorSorterData(BaseModel):
    selector_name: str
    low_limit: float
    high_limit: Optional[float] = None

    @field_validator('low_limit', 'high_limit', mode='before')
    def check_low_limit(cls, value):
        if isinstance(value, str) and value.isnumeric():
            return float(value)
        return value

    def create_sorter(self,):
        sorter = SelectorSorter(self.selector_name)
        sorter.limits = [self.low_limit, self.high_limit]
        return sorter
    
    @property
    def file_name(self):
        selector_name = self.selector_name.replace(' ', '_')
        return f'{selector_name.lower()}_data.json'

    def save(self, grid_directory):
        with open(grid_directory / self.file_name, 'w') as f:
            f.write(self.model_dump_json())

    @classmethod
    def exists(cls, directory:Path, selector_name:str):
        selector_name = selector_name.replace(' ', '_')
        return (directory / f'{selector_name.lower()}_data.json').exists()

    @classmethod
    def load(cls, directory:Path, selector_name):
        logger.info(f'Loading selector data from {directory} for {selector_name}')
        selector_name = selector_name.replace(' ', '_')
        with open(directory / f'{selector_name.lower()}_data.json', 'r') as f:
            data = f.read()
        return cls.model_validate_json(data)
    
    def delete(self, grid_directory):
        (grid_directory / self.file_name).unlink()

    @classmethod
    def parse_sorter(cls, sorter):
        return cls(selector_name=sorter.selector_name, low_limit=sorter.limits[0], high_limit=sorter.limits[1])

def save_to_grid_directory(grid_id):
    grid = models.AutoloaderGrid.objects.get(grid_id=grid_id)
    return grid.directory

def save_to_session_directory(grid_id):
    grid = models.AutoloaderGrid.objects.get(grid_id=grid_id)
    return grid.session_id.directory

def save_selector_data(grid_id, selector_name:str, data:dict,save_to:Callable=save_to_grid_directory) -> SelectorSorterData:
    selector_data = SelectorSorterData(selector_name=selector_name,**data)
    save_directory = save_to(grid_id)
    selector_data.save(save_directory)
    return selector_data

class SelectorValueParser:

    def __init__(self, selector_name:str, from_server=False):
        self._selector_name = selector_name
        self._from_server = from_server

    def get_selector_value(self,target):
        if self._from_server:
            return self.get_selector_value_from_server(target)
        return self.get_selector_value_from_worker(target)

    def get_selector_value_from_worker(self,target):
        return next(filter(lambda x: x.method_name == self._selector_name ,target.selectors)).value
    
    def get_selector_value_from_server(self,target):
        return next(filter(lambda x: x.method_name == self._selector_name ,target.selectors.all())).value
    
    def extract_values(self, targets:List[models.Target]) -> List[float]:
        values = list(map(self.get_selector_value,targets))
        if all([value == None for value in values]):
            raise LagacySorterError('No values found in targets. Reverting to lagacy sorting.')
        return values

class SelectorSorter:
    _limits = None
    _classes:List = None
    _labels:List = None
    _colors:List = None
    _values:List = None

    def __init__(self,selector_name:str, n_classes=5, fractional_limits:List[float]=None):
        self.selector_name= selector_name
        self._n_classes = n_classes
        self._fractional_limits = fractional_limits

    # def __getitem__(self, index):
    #     return self._targets[index], *self.labels[index]

    @property
    def classes(self):
        if self._classes is None:
            self.calculate_classes()
        return self._classes
    
    @property
    def labels(self):
        if self._labels is None:
            self.set_labels()
        return self._labels
    
    @property
    def limits(self):
        if self._limits is None:
            self.set_limits()
        return self._limits
    
    @property
    def colors(self):
        if self._colors is None:
            self.set_colors()
        return self._colors
    
    @property
    def values(self):
        if self._values is None:
            raise NotSetError('Values have not been set.')
        return self._values
    
    @values.setter
    def values(self, values:List[float]):
        self._values = values
    
    @limits.setter
    def limits(self, value:List[float]):
        self._limits = value
        self._classes = None

    @property
    def values_range(self) -> List[float]:
        return [floor(min(self.values)), ceil(max(self.values))]

    def set_limits(self):
        range_ = max(self.values) - min(self.values)
        self._limits = np.array(self._fractional_limits) * range_ + min(self.values)

    def set_labels(self):
        logger.debug(f'Getting colored classes from selector {self.selector_name}. Inputs {len(self.values)} targets and {self._n_classes} classes with {self.limits} limits.')
        # classes, limits = self.classes(self._targets, n_classes=n_classes, limits=limits)
        colors = self.set_colors()
        logger.debug(f'Colors are {colors}')
        colored_classes = list(map(lambda x: (colors[x], x, 'Cluster' ) if x != 0 else ((colors[x], 0, 'Rejected')), self.classes))
        logger.debug(f'Colored classes are {colored_classes}')
        self._labels = colored_classes
        return colored_classes

    def calculate_classes(self):
        # logger.debug(f'Getting classes from selector {self._selector.name}. Inputs {len(self._targets)} targets and {self._n_classes} with limits {self.limits}.')
        map_in_bounds = self.included_in_limits()
        step = np.diff(self.limits) / (self._n_classes)
        
        # for value, in_bounds in zip(values, map_in_bounds):
        def get_class(value, in_bounds) -> int:
            if not in_bounds:
                return 0
            if value == self.limits[1]:
                return self._n_classes
            return int(np.floor((value - self.limits[0]) / step) + 1)
        
        self._classes = list(map(get_class, self.values, map_in_bounds))
        logger.debug(f'Classes are {self._classes}')
        return self._classes

    # def draw(self, n_classes=5, limits=None):
    #     if hasattr(self._selector, 'drawMethod'):
    #         return self._selector.draw_method(self._targets, n_classes, limits)
    


    def included_in_limits(self):
        if self.limits is None:
            self.set_limits()
        def selector_value_within_limits(target_value):
            # logger.debug(f'Checking if {target_value} is within {self.limits}')
            return self.limits[0] <= target_value <= self.limits[1]

        selector_value_within_limits = map(selector_value_within_limits,self.values)
        return list(selector_value_within_limits)

    def set_colors(self):
        colors = list()
        cmap = cm.plasma
        cmap_step = int(floor(cmap.N / self._n_classes))
        for c in range(cmap.N, 0, -cmap_step):
            colors.append(rgb2hex(cmap(c)))
            continue

        self._colors = colors
        return colors


def check_directories_for_selector_data(grid:models.AutoloaderGrid, selector_name:str) -> Path:
    priority = [grid.directory, grid.session_id.directory]
    for directory in priority:
        if SelectorSorterData.exists(directory, selector_name):
            return directory
    

def initialize_selector(grid: models.AutoloaderGrid, selector:str, queryset) -> SelectorSorter:
    selector_sorter = SelectorSorter(selector_name=selector,fractional_limits=PLUGINS_FACTORY[selector].limits)
    directory = check_directories_for_selector_data(grid,selector)
    if directory is not None:
        selector_data = SelectorSorterData.load(directory, selector)
        selector_sorter = selector_data.create_sorter()
    selector_data = SelectorValueParser(selector, from_server=True)
    selector_sorter.values = selector_data.extract_values(queryset)
    return selector_sorter