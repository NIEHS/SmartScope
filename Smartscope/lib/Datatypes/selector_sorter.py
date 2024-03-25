import numpy as np
from typing import List
import logging
from matplotlib import cm
from matplotlib.colors import rgb2hex
from math import floor

from .base_plugin import Selector

logger = logging.getLogger(__name__)


class LagacySorterError(Exception):
    pass

class SelectorSorter:
    _limits = None
    _classes:List = None
    _labels:List = None
    _colors:List = None
    _values:List = None
    _from_server = False

    def __init__(self,selector:Selector, targets, n_classes=5, limits=None, from_server=True):
        self._selector: Selector = selector
        self._targets = targets
        self._n_classes = n_classes
        self._from_server = from_server

        if all([value == None for value in self.values]):
            raise LagacySorterError('No values found in targets. Reverting to lagacy sorting.')
        # self.set_limits()

    def __getitem__(self, index):
        return self._targets[index], *self.labels[index]

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
            self.extract_values()
        return self._values
    
    @limits.setter
    def limits(self, value:List[float]):
        self._limits = value

    def set_limits(self):
        range_ = max(self.values) - min(self.values)
        self._limits = np.array(self._selector.limits) * range_ + min(self.values)

    def set_labels(self):
        logger.debug(f'Getting colored classes from selector {self._selector.name}. Inputs {len(self._targets)} targets and {self._n_classes} classes with {self.limits} limits.')
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
        step = np.floor(np.diff(self.limits) / (self._n_classes))
        
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

    def draw(self, n_classes=5, limits=None):
        if hasattr(self._selector, 'drawMethod'):
            return self._selector.draw_method(self._targets, n_classes, limits)
    
    def get_selector_value(self,target):
        if self._from_server:
            return self.get_selector_value_from_server(target)
        return self.get_selector_value_from_worker(target)

    def get_selector_value_from_worker(self,target):
        return next(filter(lambda x: x.method_name == self._selector.name ,target.selectors)).value
    
    def get_selector_value_from_server(self,target):
        return next(filter(lambda x: x.method_name == self._selector.name ,target.selectors.all())).value
    
    def extract_values(self):
        self._values = list(map(self.get_selector_value,self._targets))

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
            prefix = ''
            val = v * self.step
            if val == self.range[0]:
                prefix = '\u2264'
            if val == self.range[1]:
                prefix = '\u2265'
            # print(f'From CTF {prefix}{v*self.step}, color is {rgb2hex(cmap(c))}')
            colors.append((rgb2hex(cmap(c)), v * self.step, prefix))

        self._colors = colors
        return colors