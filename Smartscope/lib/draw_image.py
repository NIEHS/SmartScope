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
from torch import Tensor
import logging
import pandas as pd

from Smartscope.lib.generic_position import parse_mdoc
from Smartscope.lib.Finders.basic_finders import *
from Smartscope.lib.s3functions import TemporaryS3File
from Smartscope.lib.image_manipulations import fourier_crop, save_mrc
from Smartscope.lib.transformations import closest_node, pixel_to_stage
from .base_image import BaseImage

mpl.use('Agg')
logger = logging.getLogger(__name__)



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



def plot_thresholds(
        im,
        blur,
        thresh,
        thresholded,
        cnts,
        file,
        mu=None,
        sigma=None,
        a=None,
        polygon='Circle'
    ):
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
