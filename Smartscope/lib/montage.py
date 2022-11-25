#! /usr/bin/env python
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import cv2
import mrcfile
import os
import numpy as np
import imutils
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

import pandas as pd
from Smartscope.lib.generic_position import parse_mdoc
from Smartscope.lib.Finders.basic_finders import *
from Smartscope.lib.s3functions import TemporaryS3File
from Smartscope.lib.image_manipulations import fourier_crop, save_mrc
from Smartscope.lib.transformations import closest_node, pixel_to_stage
from torch import Tensor
import logging

mpl.use('Agg')

logger = logging.getLogger(__name__)


def quantize(x, mi=-3, ma=3, dtype=np.uint8):
    x = (x - x.mean()) / (x.std())
    if mi is None:
        mi = x.min()
    if ma is None:
        ma = x.max()
    r = ma - mi
    x = 255 * (x - mi) / r
    x = np.clip(x, 0, 255)
    x = np.round(x).astype(dtype)
    return x





def plot_hist(image, size=254, **kwargs):
    mydpi = 300
    fig = plt.figure(figsize=(5, 5), dpi=mydpi)
    ax = fig.add_subplot(111)
    ax.hist(image.flatten(), bins=200, label='Distribution')
    colors = ['orange', 'green', 'red', 'black']
    for ind, (key, val) in enumerate(kwargs.items()):
        ax.axvline(val, c=colors[ind], label=key)
    ax.title.set_text('Histogram')
    ax.set_xlabel('Pixel intensity')
    ax.set_ylabel('Counts')
    ax.legend()
    ax.set_yscale('log')
    fig.canvas.draw()
    hist = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
    hist = hist.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    hist = imutils.resize(hist, height=size)
    plt.close(fig='all')
    return hist




def plot_thresholds(im, blur, thresh, thresholded, cnts, file, mu=None, sigma=None, a=None, polygon='Circle'):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(221)
    ax.imshow(im, cmap='gray')
    ax.title.set_text('Original')
    ax.axis('off')
    flat = blur.flatten()
    ax1 = fig.add_subplot(222)
    ax1.hist(flat, bins=200, label='Distribution')
    x = np.linspace(0, 255, 100)
    if all([mu is not None, sigma is not None, a is not None]):
        ax1.plot(x, gauss(x, mu, sigma, a), color='red', lw=3, label='gaussian')
    ax1.axvline(mu, c='orange', label='mean')
    ax1.axvline(thresh, c='green', label='threshold')
    ax1.title.set_text('Histogram')
    ax1.set_xlabel('Pixel intensity')
    ax1.set_ylabel('Counts')
    ax1.legend()

    ax2 = fig.add_subplot(223)
    ax2.imshow(thresholded, cmap='gray')
    ax2.title.set_text('Thresholded')
    ax2.axis('off')

    ax3 = fig.add_subplot(224)
    ax3.imshow(blur, cmap='gray')
    if polygon == 'Circle':
        for circ in cnts:
            centroid, radius = cv2.minEnclosingCircle(circ)
            p = Circle(centroid, radius, edgecolor='green', linewidth=2, fill=False, facecolor=None)
            ax3.add_patch(p)
    else:
        im_cnt = cv2.drawContours(im, cnts, -1, (0, 255, 0), 3)
        ax3.imshow(im_cnt, cmap='gray')
    ax3.title.set_text('Holes')
    ax3.axis('off')

    plt.savefig(file, bbox_inches='tight')
    plt.close(fig='all')


def round_up_to_odd(f):
    odd = np.ceil(f) // 2 * 2 + 1
    return odd.astype(int)


@dataclass
class BaseImage(ABC):

    name: str
    working_dir: str = ''
    is_movie: bool = False
    metadata: Union[pd.DataFrame, None] = None
    _raw = None
    _mdoc = None

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, value):
        self._directory = value

    @property
    def image_path(self):
        return self._image_path

    @image_path.setter
    def image_path(self, value):
        self._image_path = value

    @property
    def metadataFile(self):
        return self._metadataFile

    @metadataFile.setter
    def metadataFile(self, value):
        self._metadataFile = value

    @property
    def png(self):
        return Path(self.working_dir, 'pngs', f'{self.name}.png')

    @property
    def raw(self):
        if self._raw is not None:
            return self._raw
        return Path(self.working_dir, 'raw', f'{self.name}.mrc')
    
    @raw.setter
    def raw(self, value):
        self._raw = value 
        self._mdoc = Path(str(value) + '.mdoc')

    @property
    def mdoc(self):
        if self._mdoc is not None:
            return self._mdoc
        return Path(self.working_dir, 'raw', f'{self.name}.mrc.mdoc')

    @property
    def shape_x(self):
        return self.image.shape[0]

    @property
    def shape_y(self):
        return self.image.shape[1]
    
    @property
    def center(self):
        return np.array([self.shape_x//2, self.shape_y//2],dtype=int)

    # @property
    # def image_center(self):
    #     return np.array([self.shape_x, self.shape_y]) // 2

    @property
    def rotation_angle(self):
        return self.metadata.iloc[0].RotationAngle

    def get_tile(self, tileIndex=0):
        return self.metadata.iloc[tileIndex]

    @property
    def stage_z(self):
        return self.metadata.iloc[0].StageZ

    @property
    def pixel_size(self):
        return self.metadata.iloc[0].PixelSpacing

    @property
    def ctf(self):
        return Path(self.directory, 'ctf.txt')

    def read_image(self):
        try:
            with mrcfile.open(self.image_path) as mrc:
                self.image = mrc.data
        except FileNotFoundError:
            with mrcfile.open(self.raw) as mrc:
                self.image = mrc.data            
        return

    def read_data(self):
        self.read_image()
        self.read_metadata()

    def downsample(self, scale=2) -> np.ndarray:
        return fourier_crop(self.image, height=int(self.shape_x // scale))

    def check_metadata(self, check_AWS=False):
        if self.image_path.exists() and self.metadataFile.exists():
            logger.info('Found metadata, reading...')
            self.read_data()
            return True

        if check_AWS:
            logger.debug(f'{self.image_path}, {self.metadataFile}')
            with TemporaryS3File([self.image_path, self.metadataFile]) as temp:
                self.image_path, self.metadataFile = temp.temporary_files
                self.read_data()

            return True
        return False

    def save_metadata(self):
        self.metadata.to_pickle(self.metadataFile)

    def read_metadata(self):
        self.metadata = pd.read_pickle(self.metadataFile)

    def make_symlink(self):
        relative = os.path.relpath(self.raw,self.directory)
        logger.debug(f'Relative path from {self.directory} to raw = {relative}')
        os.symlink(relative, self.image_path)

    def __post_init__(self):
        self._directory = Path(self.working_dir, self.name)
        self._image_path = Path(self._directory, f'{self.name}.mrc')
        self._metadataFile = Path(self._directory, f'{self.name}_metadata.pkl')


@dataclass
class Montage(BaseImage):

    def __post_init__(self):
        super().__post_init__()
        self.directory.mkdir(exist_ok=True)

    def load_or_process(self, check_AWS=False):
        if self.check_metadata(check_AWS=check_AWS):
            return
        self.metadata = parse_mdoc(self.mdoc, self.is_movie)
        self.build_montage()
        self.read_image()
        self.save_metadata()

    def build_montage(self):

        def piece_pos(piece):
            piece_coord = np.array(piece.PieceCoordinates[0: -1])
            piece_coord_end = piece_coord + np.array([self.header.mx, self.header.my])
            piece_pos = np.array([piece_coord, [piece_coord[0], piece_coord_end[1]], piece_coord_end, [piece_coord_end[0], piece_coord[1]]])
            return piece_pos

        def piece_center(piece):
            return np.array([np.sum(piece[:, 0]) / piece.shape[0], np.sum(piece[:, 1]) / piece.shape[0]])

        with mrcfile.open(self.raw) as mrc:
            self.header = mrc.header
            img = mrc.data
        if int(self.header.mz) == 1:
            self.metadata['PieceCoordinates'] = [[0, 0, 0]]
            self.metadata['piece_limits'] = self.metadata.apply(piece_pos, axis=1)
            self.metadata['piece_center'] = self.metadata.piece_limits.apply(piece_center)
            montage = img
            self.image = montage
            self.make_symlink()
            return

        self.metadata['piece_limits'] = self.metadata.apply(piece_pos, axis=1)
        self.metadata['piece_center'] = self.metadata.piece_limits.apply(piece_center)
        montsize = np.array([0, 0])
        for _, piece in enumerate(self.metadata.piece_limits):
            for ind, i in enumerate(piece[2]):
                if i > montsize[ind]:
                    montsize[ind] = i
        montage = np.empty(np.flip(montsize), dtype='int16')
        for ind, piece in enumerate(self.metadata.piece_limits):
            montage[piece[0, 1]: piece[-2, 1], piece[0, 0]: piece[-2, 0]] = img[ind, :, :]
        montage = montage[~np.all(montage == 0, axis=1)]
        montage = montage[:, ~(montage == 0).all(0)]

        self.image = montage

        save_mrc(self.image_path, self.image, self.pixel_size, [0, 0])


@dataclass
class Movie(BaseImage):

    is_movie: bool = True

    @property
    def shifts(self):
        return Path(self.directory, 'ali.xf')

    def __post_init__(self):
        super().__post_init__()
        self.directory.mkdir(exist_ok=True)

    def check_metadata(self):
        if self.image_path.exists() and self.shifts.exists() and self.ctf.exists():
            return True


def create_targets_from_box(targets: List, montage: BaseImage, target_type: str = 'square'):
    output_targets = []
    if isinstance(targets, tuple):
        targets, labels = targets
    else:
        labels = [None] * len(targets)
    for target, label in zip(targets, labels):
        t = Target(target, quality=label)
        t.convert_image_coords_to_stage(montage)
        t.set_area_radius(target_type)
        output_targets.append(t)

    output_targets.sort(key=lambda x: (x.stage_x, x.stage_y))

    return output_targets

def create_targets_from_center(targets: List, montage: BaseImage):
    output_targets = []

    for target in targets:
        t = Target(target,from_center=True)
        t.convert_image_coords_to_stage(montage)
        output_targets.append(t)

    output_targets.sort(key=lambda x: (x.stage_x, x.stage_y))

    return output_targets    


class Target:

    _x: Union[int,None] = None
    _y: Union[int,None] = None
    shape: Union[list, Tensor]
    quality: Union[str, None] = None
    area: Union[float, None] = None
    radius: Union[float, None] = None
    stage_x: Union[float, None] = None
    stage_y: Union[float, None] = None
    stage_z: Union[float, None] = None

    def __init__(self,shape: Union[list, Tensor], quality: Union[str,None]=None, from_center=False) -> None:
        self.quality = quality
        if from_center:
            self.x = shape[0]
            self.y = shape[1]
            return
        self.x = shape
        self.y = shape
        self.shape = shape


    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value = None):
        if isinstance(value,list):
            self._x = int(value[0] + (value[2] - value[0]) // 2)
        self._x = value    

    @property
    def y(self):
        return self._y
    
    @property
    def coords(self):
        return np.array([self._x,self._y])

    @y.setter
    def y(self, value = None):
        if isinstance(value,list):
            self._y = int(value[1] + (value[3] - value[1]) // 2)
        self._y = value

    def set_area_radius(self, shape_type):

        len1 = int(self.shape[2] - self.shape[0])
        len2 = int(self.shape[3] - self.shape[1])

        if shape_type == 'square':
            self.area = len1 * len2
            return

        if shape_type == 'hole':

            self.radius = min(len1, len2) / 2
            self.area = np.pi * (self.radius ** 2)
            return

    def convert_image_coords_to_stage(self, montage):
        tile, dist = closest_node([self.x, self.y], montage.metadata.piece_center)
        self.stage_x, self.stage_y = pixel_to_stage(dist, montage.metadata.iloc[tile], montage.metadata.iloc[tile].TiltAngle)
        self.stage_z = montage.stage_z
