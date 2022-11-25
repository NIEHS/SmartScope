#! /usr/env/bin python
from pathlib import Path
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


def export_as_png(image, output, height=1024, normalization=auto_contrast, binning_method=imutils.resize) -> Path:
    resized = normalization(binning_method(image, height=height))
    cv2.imwrite(str(output), resized)
    return output


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


def generate_hole_ref(hole_size_in_um: float, pixel_size: float, out_type: str = 'int16'):
    radius = int(hole_size_in_um / (pixel_size / 10_000) / 2)
    im_size = int(radius * 2.5)
    fill_value = 2 ** np.dtype(out_type).itemsize
    color = 0
    if np.issubdtype(out_type, np.signedinteger):
        fill_value /= 2
        color = -fill_value

    im = np.ones((im_size, im_size)) * int(fill_value)

    cv2.circle(im, (im_size // 2, im_size // 2), radius=radius, color=int(color), thickness=max([1, int(80 / pixel_size)]))
    return im.astype(out_type)

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