#! /usr/bin/env python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import time
from typing import List, Union
import cv2
import mrcfile
import os
import io
import numpy as np
import imutils
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from scipy.optimize import curve_fit
from math import radians, sin, cos, floor, sqrt, degrees, atan2
from scipy.spatial.distance import cdist
import pandas as pd
import math
from Smartscope.lib.generic_position import parse_mdoc
from Smartscope.lib.Classifiers.basic_pred import decide_type
from Smartscope.lib.Finders.basic_finders import *
from Smartscope.lib.image_manipulations import save_mrc, to_8bits, auto_contrast, auto_contrast_sigma, save_image, mrc_to_png, fourier_crop
from torch import Tensor
import logging

mpl.use('Agg')

logger = logging.getLogger(__name__)


def convert_centers_to_boxes(center: np.ndarray, pixel_size_in_angst: float, max_x: float, max_y: float, diameter_in_um: float = 1.2) -> np.ndarray:
    radius_in_pix = int(diameter_in_um * 10000 / pixel_size_in_angst // 2)
    left = max([0, center[1] - radius_in_pix])
    up = max([0, center[0] - radius_in_pix])
    right = min([max_x, center[1] + radius_in_pix])
    down = min([max_y, center[0] + radius_in_pix])
    return np.array([up, left, down, right])


def auto_canny(image, limits=None, sigma=0.33, dilation=5):
    # compute the median of the single channel pixel intensities
    v = np.median(image)
    if limits is None:
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
    else:
        lower = min(limits)
        upper = max(limits)
    edged = cv2.Canny(image, lower, upper)

    if dilation is None:
        return edged, lower, upper
    else:
        kernel = np.ones((dilation, dilation), np.uint8)
        dilated = cv2.dilate(edged, kernel, iterations=1)
        erosion = cv2.erode(dilated, kernel, iterations=1)
        return erosion, lower, upper


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


def closest_node(node, nodes, num=1):
    nodes = np.stack((nodes))
    cd = cdist([node], nodes)
    index = cd.argmin()
    dist = nodes[index] - node
    return index, dist


def pixel_to_stage(dist, tile, tiltAngle):
    apix = tile.PixelSpacing / 10000
    dist *= apix
    theta = radians(tile.RotationAngle)
    c, s = cos(theta), sin(theta)
    R = np.array(((c, -s), (s, c)))
    specimen_dist = np.sum(R * np.reshape(dist, (-1, 1)), axis=0)
    coords = tile.StagePosition + specimen_dist / np.array([1, cos(radians(round(tiltAngle, 1)))])
    return np.around(coords, decimals=3)


def find_contours(im, thresh):
    thresh = cv2.threshold(im, thresh, 255, cv2.THRESH_BINARY)[1]
    t = cv2.convertScaleAbs(thresh)
    cnts = cv2.findContours(t.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    return cnts, t


def gauss(x, mu, sigma, A):
    return A * np.exp(- ((x - mu) ** 2) / (2 * sigma ** 2))


def fit_gauss(blur, min=40, max=255):
    bins = max - min
    flat_blur = blur.flatten()
    flat_blur = flat_blur[(flat_blur > min) & (flat_blur < max)]
    y, x, _ = plt.hist(flat_blur, bins=bins)
    peak = np.argmax(y)
    amax = np.max(y)
    std = [-1, -1]
    for i in range(peak, int(bins), 1):
        if y[i] <= amax * 0.25:
            std[1] = i - peak
            break
    for i in range(peak, 0, -1):
        if y[i] <= amax * 0.25:
            std[0] = peak - i
            break

    std = np.mean(np.array([abs(i) for i in std if i >= 0]))

    expected = (x[peak], std, amax)
    try:
        params, cov = curve_fit(gauss, x[:-1], y, expected)
        return params, True
    except Exception as err:
        logger.debug('Could not fit gaussian, passing expected params')
        return expected, False


def plot_hist_gauss(image, thresh, mu=None, sigma=None, a=None, size=254):
    mydpi = 300
    fig = plt.figure(figsize=(5, 5), dpi=mydpi)
    ax = fig.add_subplot(111)
    flat = image.flatten()
    ax.hist(flat, bins=200, label='Distribution')
    x = np.linspace(0, 255, 100)
    if all([mu is not None, sigma is not None, a is not None]):
        ax.plot(x, gauss(x, mu, sigma, a), color='red', lw=3, label='gaussian')

    if mu is None:
        mu = np.mean(flat)
    ax.axvline(mu, c='orange', label='mean')
    ax.axvline(thresh, c='green', label='threshold')
    ax.title.set_text('Histogram')
    ax.set_xlabel('Pixel intensity')
    ax.set_ylabel('Counts')
    ax.legend()
    fig.canvas.draw()
    hist = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
    hist = hist.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    hist = imutils.resize(hist, height=size)
    plt.close(fig='all')
    return hist


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


def gaussian_kernel(size, sigma, two_d=True):
    'returns a one-dimensional gaussian kernel if two_d is False, otherwise 2d'
    if two_d:
        kernel = np.fromfunction(lambda x, y: (1 / (2 * math.pi * sigma**2)) * math.e **
                                 ((-1 * ((x - (size - 1) / 2)**2 + (y - (size - 1) / 2)**2)) / (2 * sigma**2)), (size, size))
    else:
        kernel = np.fromfunction(lambda x: math.e ** ((-1 * (x - (size - 1) / 2)**2) / (2 * sigma**2)), (size,))
    return kernel / np.sum(kernel)


def power_spectrum(im):
    f = np.fft.fft2(im)
    fshift = np.fft.fftshift(f)
    fabs = np.abs(fshift)
    contrasted = auto_contrast_sigma(fabs, sigmas=0.5, to_8bits=True)
    img = imutils.resize(contrasted, height=800)
    is_succes, buffer = cv2.imencode(".png", img)
    return io.BytesIO(buffer)


def highpass(im, pixel_size, filter_size=4):
    f = np.fft.fft2(im)
    fshift = np.fft.fftshift(f)
    fabs = np.abs(fshift)
    fang = np.angle(fshift)

    size = pixel_size / 10000 / filter_size * np.array(im.shape)
    size = round_up_to_odd(size)

    center = np.floor(np.array(im.shape) / 2).astype(int)
    high = np.ones(im.shape)
    cv2.ellipse(high, (center[0], center[1]), (size[0], size[1]), 0.0, 0.0, 360.0, 0, -1)
    padding = np.array(high.shape) * 0.002
    padding = padding.astype(int)
    high[center[0] - padding[0]:center[0] + padding[0], :] *= 0.2
    high[:, center[1] - padding[1]:center[1] + padding[1]] *= 0.2
    fabs *= high
    fabs = auto_contrast(fabs, cutperc=[90, 0.001], to_8bits=True)
    F = fabs * np.exp(1j * fang)
    reversed = to_8bits(np.real(np.fft.ifft2(np.fft.ifftshift(F))))
    return reversed, fabs


def find_pattern(image, apix, plot=False, saveLoc=None, thresh=100, highpass_res=4):
    smallest_distance = 0
    smallest_distance_pix = 0
    stack = None
    angle = 0
    hp, fft = highpass(image, apix, filter_size=highpass_res)

    center = np.array(fft.shape) // 2
    cropped = fft[center[0]:center[0] + int(center[0] // 2), center[1]:center[1] + int(center[1] // 2)]
    cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_GRAY2RGB)
    cnts, t = find_contours(cropped, thresh)

    min_t, max_t = cropped.shape[0] * 0.005, cropped.shape[0] * 0.05
    cnts = [cnt for cnt in cnts if (min_t <= cv2.contourArea(cnt) <= max_t)]

    for cnt in cnts:
        cv2.drawContours(cropped_rgb, [cnt], -1, (255, 0, 0))
        mask = np.zeros(cropped.shape, np.uint8)
        cv2.drawContours(mask, [cnt], 0, 255, -1)
        _, max_val, _, max_loc = cv2.minMaxLoc(cropped, mask=mask)
        if 0 not in max_loc and max_val > 100:
            cropped_rgb[max_loc[::-1]] = [0, 0, 255]
            dist_pix = np.sqrt(np.sum((np.array(max_loc) / np.array(image.shape))**2))
            dist = 1 / dist_pix * apix / 10000
            ang = degrees(atan2(*max_loc[::-1]))

            if dist > smallest_distance:
                smallest_distance = dist
                smallest_distance_pix = np.array(max_loc)
                angle = ang

    if plot:
        extracted_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        hp_rgb = cv2.cvtColor(to_8bits(hp), cv2.COLOR_GRAY2RGB)
        fft_rgb = cv2.cvtColor(fft, cv2.COLOR_GRAY2RGB)
        hist_cropped = plot_hist(cropped, size=image.shape[0], threshold=thresh)
        crop_rgb = imutils.resize(cropped_rgb, height=image.shape[0])
        stack = np.hstack([extracted_rgb, hp_rgb, fft_rgb, crop_rgb, hist_cropped])
        if saveLoc is not None:
            cv2.imwrite(saveLoc, stack)
    if len(cnts) > 0:
        return smallest_distance, angle, smallest_distance_pix
    else:
        return None, None, None


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
    # fourier_crop: bool = False
    is_movie: bool = False
    metadata: Union[pd.DataFrame, None] = None

    @property
    def directory(self):
        return Path(self.working_dir, self.name)

    @property
    def image_path(self):
        return Path(self.directory, f'{self.name}.mrc')

    @property
    def metadataFile(self):
        return Path(self.directory, f'{self.name}_metadata.pkl')

    @property
    def png(self):
        return Path(self.working_dir, 'pngs', f'{self.name}.png')

    @property
    def raw(self):
        return Path(self.working_dir, 'raw', f'{self.name}.mrc')

    @property
    def mdoc(self):
        return Path(self.working_dir, 'raw', f'{self.name}.mrc.mdoc')

    @property
    def shape_x(self):
        return self.image.shape[0]

    @property
    def shape_y(self):
        return self.image.shape[1]

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
        with mrcfile.open(self.image_path) as mrc:
            self.image = mrc.data

    def read_data(self):
        self.read_image()
        self.read_metadata()

    def check_metadata(self):
        if self.image_path.exists() and self.metadataFile.exists():
            logger.info('Found metadata, reading...')
            self.read_data()
            return True
        return False

    def save_metadata(self):
        self.metadata.to_pickle(self.metadataFile)

    def read_metadata(self):
        self.metadata = pd.read_pickle(self.metadataFile)

    def export_as_png(self, height=1024, normalization=auto_contrast, binning_method=imutils.resize):
        resized = normalization(binning_method(self.image, height=height))
        cv2.imwrite(str(self.png), resized)

    def make_symlink(self):
        os.symlink(f'../raw/{self.name}.mrc', self.image_path)


@dataclass
class Montage(BaseImage):

    def __post_init__(self):
        self.directory.mkdir(exist_ok=True)
        if self.check_metadata():
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
        self.directory.mkdir(exist_ok=True)

    def check_metadata(self):
        if self.image_path.exists() and self.shifts.exists() and self.ctf.exists():
            return True


def find_targets(montage: Montage, methods: list):
    logger.debug(f'Using method: {methods}')
    for method in methods:
        if not 'args' in method.keys():
            method['args'] = []
        if not 'kwargs' in method.keys():
            method['kwargs'] = dict()

        import_cmd = f"from {method['package']} import {method['method']}"
        logger.debug(import_cmd)
        logger.debug(f"kwargs = {method['kwargs']}")
        exec(import_cmd)
        try:
            output, success, targets_class = locals()[method['method']](montage, *method['args'], **method['kwargs'])
        except Exception as err:
            logger.exception(err)
            continue
        if success:
            logger.debug(f'{method} was successful: {success}')
            return output, method['name'], method['name'] if 'Classifier' in method['targetClass'] else None, targets_class


def create_targets(targets: List, montage: BaseImage, target_type: str = 'square'):
    output_targets = []
    if isinstance(targets, tuple):
        targets, labels = targets
    else:
        labels = [None] * len(targets)
    for target, label in zip(targets, labels):
        t = AITarget(target, quality=label)
        t.convert_image_coords_to_stage(montage)
        t.set_area_radius(target_type)
        output_targets.append(t)

    output_targets.sort(key=lambda x: (x.stage_x, x.stage_y))

    return output_targets


@dataclass
class AITarget:

    shape: Union[list, Tensor]
    quality: Union[str, None] = None
    area: Union[float, None] = None
    radius: Union[float, None] = None
    stage_x: Union[float, None] = None
    stage_y: Union[float, None] = None
    stage_z: Union[float, None] = None

    @property
    def x(self):
        return int(self.shape[0] + (self.shape[2] - self.shape[0]) // 2)

    @property
    def y(self):
        return int(self.shape[1] + (self.shape[3] - self.shape[1]) // 2)

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
