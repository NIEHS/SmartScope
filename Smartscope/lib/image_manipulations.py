#! /usr/env/bin python
import mrcfile
import numpy as np
from math import floor
import os
import cv2
import imutils


def convert_centers_to_boxes(center: np.ndarray, pixel_size_in_angst: float, max_x: float, max_y: float, diameter_in_um: float = 1.2) -> np.ndarray:
    radius_in_pix = int(diameter_in_um * 10000 / pixel_size_in_angst // 2)
    left = max([0, center[1] - radius_in_pix])
    up = max([0, center[0] - radius_in_pix])
    right = min([max_x, center[1] + radius_in_pix])
    down = min([max_y, center[0] + radius_in_pix])
    return np.array([up, left, down, right])


def extract_from_image(image, center: tuple, apix: float, binned_apix: float = -1, box_size: float = 2):
    if binned_apix == -1:
        binned_apix = apix
    unbinned_centroid = np.array(center) * binned_apix // apix
    box_size = box_size / (apix / 10000) // 2
    topleft = unbinned_centroid - box_size
    topleft = tuple(topleft.astype(int))
    botright = unbinned_centroid + box_size
    botright = tuple(botright.astype(int))
    return image[topleft[1]:botright[1], topleft[0]:botright[0]], apix, box_size, topleft


def save_mrc(file, image, apix, start_values, overwrite=True):
    with mrcfile.new(file, overwrite=overwrite) as mrc:
        mrc.set_data(image)
        header = mrc.header
        header.nxstart = start_values[1]
        header.nystart = start_values[0]
        header.cella = (apix * header.nx, apix * header.ny, apix * header.nz)
        header.mx = header.nx
        header.my = header.ny


def to_8bits(image):
    img = image.astype('float64')
    img -= img.min()
    img *= 255.0 / img.max()
    img = np.round(img).astype('uint8')
    return img


def auto_contrast(img, cutperc=[0.05, 0.01], to_8bits=True):
    hist, x = np.histogram(img.flatten(), bins=256)
    total = np.sum(hist)
    min_side = 0
    min_accum = 0
    max_side = 255
    max_accum = 0
    while min_accum < cutperc[0]:
        min_accum += hist[min_side] / total * 100
        min_side += 1

    while max_accum < cutperc[1]:
        max_accum += hist[max_side] / total * 100
        max_side -= 1
    # print(f'Using auto_contrast {min_side} ({x[min_side]}), {max_side} ({x[max_side]})')
    max_side = x[max_side] - x[min_side]
    img = (img.astype('float32') - x[min_side]) / max_side
    img[img < 0] = 0
    img[img > 1] = 1
    if to_8bits is True:
        return np.round(img * 255).astype('uint8')
    else:
        return img


def auto_contrast_sigma(img, sigmas=3, to_8bits=True):
    mean = floor(np.mean(img))
    sigma = floor(np.std(img))
    im_max = np.max(img)
    im_min = np.min(img)

    min_side = max(im_min, mean - sigmas * sigma)
    max_side = min(im_max, mean + sigmas * sigma) - min_side

    img = (img.astype('float32') - min_side) / (max_side)
    img[img < 0] = 0
    img[img > 1] = 1
    if to_8bits is True:
        return np.round(img * 255).astype('uint8')
    else:
        return img


def save_image(img, filename, extension='png', resize_to: int = None, destination=None):
    if resize_to is not None:
        img = imutils.resize(img, width=resize_to)

    if destination is None:
        destination = 'pngs'
    file = os.path.join(destination, f'{filename}.{extension}')
    if os.path.isfile(file):
        os.rename(file, os.path.join(destination, f'{filename}_old.{extension}'))
    cv2.imwrite(file, img)


def mrc_to_png(mrc_file, ):
    with mrcfile.open(mrc_file) as mrc:
        img = mrc.data[0]
    img = to_8bits(img)
    save_image(img, mrc_file.replace('.mrc', ''), destination='')


def fourier_crop(img, height=500):
    ch, cw = np.array(img.shape) // 2
    width = floor(height * cw / ch)

    f = np.fft.fft2(img)
    fshift = np.fft.fftshift(f)

    cropped = fshift[int(ch - height // 2):int(ch + height // 2), int(cw - width // 2):int(cw + width // 2)]

    reversed = np.real(np.fft.ifft2(np.fft.ifftshift(cropped)))
    return reversed
