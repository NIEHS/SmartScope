import numpy as np
import matplotlib.pyplot as plt
from typing import List, Union
from dataclasses import dataclass
from matplotlib.patches import Circle, Rectangle
from pathlib import Path
import logging
import time

logger = logging.getLogger(__name__)

@dataclass
class FastAtlas:
    _max_radius_in_um:int = 990
    atlas_imsize_x:int = 5700
    atlas_imsize_y:int = 4096
    pixel_size_in_angst:float = 650
    overlap_fraction:float = 0.05
    _lattice_mask = None

    @property
    def pixel_size_um(self):
        return self.pixel_size_in_angst/10_000

    @property
    def imsize_x_um(self):
        return self.atlas_imsize_x * self.pixel_size_um
    
    @property
    def imsize_y_um(self):
        return self.atlas_imsize_y * self.pixel_size_um

    @property
    def imsize(self):
        return np.array([self.imsize_x_um,self.imsize_y_um])
    
    @property
    def lattice_mask(self):
        if self._lattice_mask is not None:
            return self._lattice_mask
        raise ValueError('Lattice mask was not set. Please use generate_tile_mask method')

    @property
    def lattice_mask_center(self):
        return np.array(self.lattice_mask.shape)//2


    def generate_tile_mask(self, atlas_radius_in_um:int = 600) -> np.ndarray:
        padded_max_axis = max([int(self._max_radius_in_um*2//self.imsize_x_um*(1-self.overlap_fraction)), int(self._max_radius_in_um*2//self.imsize_y_um*(1-self.overlap_fraction))]) + 2
        lattice_mask = np.zeros((padded_max_axis,padded_max_axis))
        center = np.array(lattice_mask.shape)//2
        
        for x,xval in enumerate(lattice_mask):
            for y,yval in enumerate(xval):
                coord = (np.array([x,y])-center) * self.imsize
                dist = np.sqrt(np.sum(np.power(coord,2)))
                if dist > atlas_radius_in_um:
                    continue
                lattice_mask[x,y] = 1
        self._lattice_mask = lattice_mask
        return self.lattice_mask

    def make_stage_pattern(self, pattern_method: callable):
        self.movements = pattern_method(self.lattice_mask)
        self.stage_movements = (np.array(self.movements)-self.lattice_mask_center) * self.imsize*(1-self.overlap_fraction)
    
    def plot_movements_on_stage(self, export_to:Union[Path,None]=None):
        fig = plt.figure(figsize=(10,10))
        ax = fig.add_subplot(111)
        limits = Circle([0,0],self.atlas_radius_in_um,fill=False)
        ax.add_patch(limits)
        ax.set_ylim(-self._max_radius_in_um,self._max_radius_in_um)
        ax.set_xlim(-self._max_radius_in_um,self._max_radius_in_um)
        for i, mov in enumerate(self.movements):
            a = (np.array(mov)-self.lattice_mask_center) * self.imsize*(1-self.overlap_fraction)
            ax.text(a[0,0],a[0,1], i+1)
            ax.plot(a[:,0],a[:,1], marker='o')
        if export_to is not None:
            fig.savefig(str(export_to),dpi=100,pad_inches=0, bbox_inches='tight')


def make_spiral_pattern_in_mask(mask:np.ndarray) -> List:
    start = np.array(mask.shape) // 2
    ind = 1
    movements = []
    while True:
        if ind+1 >= max(mask.shape):
            break
        
        for i in [np.array([1,0]),np.array([0,1])]:
            axis = np.where(i == 1)[0]
            temp_ind = ind
            if ind % 2 == 0:
                temp_ind *=-1
                
            end=start+(i*temp_ind)

            if start[0] == end[0]:
                order= np.sort(np.array([start[1],end[1]]))
                mov_slice = (start[0],slice(order[0],order[1],None))
            else:
                order= np.sort(np.array([start[0],end[0]]))
                mov_slice = (slice(order[0],order[1],None), start[1])

            if (mask[mov_slice] != 0).any():
                indexes = np.where(mask[mov_slice] == 1)[0]
                new_start, new_end = start.copy(), end.copy()
                new_start[axis] = start[axis]+indexes[0] if temp_ind > 0 else start[axis]-indexes[0]
                new_end[axis] = new_start[axis] + len(indexes) -1 if temp_ind > 0 else new_start[axis] - len(indexes) +1
                movements.append([new_start,new_end])
            start=end
        ind += 1 
    return movements

def make_serpent_pattern_in_mask(mask:np.ndarray) -> List:
    movement_direction = 1
    movements =[]
    for ind,line in enumerate(mask):
        if (line != 0).any():
            indexes = np.where(line == 1)[0]
            start = [ind,indexes[0] if movement_direction == 1 else indexes[-1]]
            end = [ind, indexes[-1] if movement_direction == 1 else indexes[0]]
            movements.append([start,end])
            movement_direction *= -1
    return movements








