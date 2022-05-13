import cv2
import numpy as np
import imutils
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from math import floor, degrees, atan, cos, sin, radians
from .calc_angle_spacing import calc_angle_spacing
from Smartscope.lib.image_manipulations import to_8bits, auto_contrast

mpl.use('Agg')


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
    except Exception:
        print('Could not fit gaussian, passing expected params')
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


def find_squares(montage, threshold=30):
    if 'threshold' in montage.__dict__:
        threshold = montage.threshold

    blurred = cv2.GaussianBlur(montage.montage, (5, 5), 0)

    cnts, _ = find_contours(blurred, threshold)
    cnts = [cnt for cnt in cnts if (montage.area_threshold[0] * 0.5 < cv2.contourArea(cnt))]

    print(f'{montage._id}, {len(cnts)} targets found')
    return cnts, True, 'SquareTarget', None


def find_square(montage):
    thresh = np.mean(montage.montage)
    hist = plot_hist_gauss(montage.montage, thresh, size=montage.montage.shape[0])
    contours, _ = find_contours(montage.montage, thresh)
    contour = [cnt for cnt in contours if (1000 < cv2.contourArea(cnt))][0]
    M = cv2.moments(contour)
    cX = int(M["m10"] / M["m00"])
    cY = int(M["m01"] / M["m00"])
    return contour, np.array([cX, cY]), hist


def find_targets_binary(montage, threshold=30, save=False):
    """ Finds holes by applying a binary threshold on the image. The threshold is automatically evaluated based on the gaussian curve fitting on the pixel intensity histogram. """
    _, centroid, _ = find_square(montage)
    blurred = cv2.GaussianBlur(montage.montage, (5, 5), 0)
    result = cv2.cvtColor(montage.montage.copy(), cv2.COLOR_GRAY2RGB)
    done = False

    (mu, sigma, a), is_fit = fit_gauss(blurred)
    if mu < 100:
        sig = 5
    else:
        sig = 3

    while not done:
        threshold = mu + sigma * sig

        cnts, t = find_contours(blurred, threshold)
        cnts = [cnt for cnt in cnts if (75 < cv2.contourArea(cnt) < 500)]
        for cnt in cnts:
            cv2.drawContours(result, [cnt], -1, (0, 255, 0), cv2.FILLED)

        if len(cnts) < 90 and sig > 2:
            sig -= 0.5
        else:
            done = True

    if len(cnts) < 30:
        return None, False, None, None

    return cnts, True, 'HoleTarget', centroid


def fourrier_filter(im, ang, coords):
    f = np.fft.fft2(im)
    fshift = np.fft.fftshift(f)
    fang = np.angle(fshift)

    fft_test = np.zeros(im.shape, dtype=np.uint8)
    center = np.floor(np.array(fft_test.shape) / 2).astype(int)
    try:
        i, j = coords
        dist = sqrt(i**2 + j**2)
    except:
        dist = coords

    for ind in range(1, 5, 1):
        angle = ang + (90 * ind)
        x = int(round(dist * cos(radians(angle))))
        y = int(round(dist * sin(radians(angle))))
        fft_test[center[0] + y, center[1] + x] = 255
    F = fft_test * np.exp(1j * fang)
    reversed = to_8bits(np.real(np.fft.ifft2(np.fft.ifftshift(F))))
    rev = abs(reversed / 255)
    rev[rev < 0.7] = 0
    rev[rev >= 0.7] = 1
    return rev


def fft_method(montage):
    """ Finds the spacing and angle by finding peaks in the 2D power spectrum of the image. """
    orientation, spacing, square_cont, ratio = calc_angle_spacing(montage.raw_montage)
    square_angle = square_cont[0] - square_cont[1]
    square_angle = degrees(atan(square_angle[0] / square_angle[1]))
    square_cont = square_cont // montage.binning_factor
    square_cont = square_cont.astype(int)
    centroid = np.array([np.sum(square_cont[:, 0]) / square_cont.shape[0],
                         np.sum(square_cont[:, 1]) / square_cont.shape[0]]).astype(int)
    dist_pix = 1 / spacing / ratio
    dist = dist_pix / (montage.pixel_size / 10000)
    orientation = 90 - square_angle - orientation
    print(f'Found holey pattern of {round(dist,2)} \u03BCm at {round(orientation,2)}\u00B0')
    pattern_filter = fourrier_filter(montage.montage, orientation, 1 / dist_pix)
    product = pattern_filter * montage.montage
    cnts, t = find_contours(product, 80)
    cnts = [cnt for cnt in cnts if (75 < cv2.contourArea(cnt) < 2000)]
    return cnts, True, 'HoleTarget', centroid


def regular_pattern(montage, spacing=5):
    """ Applies a regular pattern of targets on the image. """
    _, centroid, _ = find_square(montage)
    spacing *= 10000
    target_area = int(floor(5000 / montage.apix))
    pixel_spacing = int(floor(spacing / montage.apix))
    n_pt = np.floor(montage.binned_size / pixel_spacing).astype(int)

    # thresh = cv2.threshold(montage.montage, mu - 4 * sigma, 255, cv2.THRESH_BINARY)[1]
    # t = cv2.convertScaleAbs(thresh)
    ar = []
    for x in range(n_pt[1]):
        x *= pixel_spacing
        for y in range(n_pt[0]):
            y *= pixel_spacing
            m = np.mean(montage.montage[y - target_area:y + target_area, x - target_area:x + target_area])
            if m > 120:
                ar.append([x, y])
    array = np.array(ar) * montage.binning_factor
    # array *= montage.binning_factor
    return array, True, 'LatticeTarget', centroid


def find_square_center(img):
    img = auto_contrast(img)
    thresh = np.mean(img)
    # hist = plot_hist_gauss(montage.montage, thresh, size=montage.montage.shape[0])
    contours, _ = find_contours(img, thresh)
    areas = [cv2.contourArea(cnt) for cnt in contours]
    largest_contour = contours[areas.index(max(areas))]
    M = cv2.moments(largest_contour)
    cX = int(M["m10"] / M["m00"])
    cY = int(M["m01"] / M["m00"])
    return np.array([cX, cY])
