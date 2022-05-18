import os
import glob
import mrcfile
#from Smartscope.Montage import *
#from Smartscope.auto_screen import *
import cv2
import shutil
import numpy as np
import cv2
import os.path
import matplotlib.pyplot as plt
from sklearn.neighbors import KernelDensity
from skimage.util import img_as_ubyte
from skimage.morphology import convex_hull_image
import mrcfile
from pyampd.ampd import find_peaks


def smooth(x, window_len=11, window='hanning'):
    """smooth the data using a window with requested size.

    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal 
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.

    input:
        x: the input signal 
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal

    example:

    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)

    see also: 

    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    scipy.signal.lfilter

    TODO: the window parameter could be the window itself if an array instead of a string
    NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
    """

    if x.ndim != 1:
        raise (ValueError, "smooth only accepts 1 dimension arrays.")

    if x.size < window_len:
        raise (ValueError, "Input vector needs to be bigger than window size.")

    if window_len < 3:
        return x

    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise (ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")

    s = np.r_[x[window_len-1:0:-1], x, x[-2:-window_len-1:-1]]
    # print(len(s))
    if window == 'flat':  # moving average
        w = np.ones(window_len, 'd')
    else:
        w = eval('np.'+window+'(window_len)')

    y = np.convolve(w/w.sum(), s, mode='valid')
    return y[(window_len//2):-(window_len//2)]


def decide_type(img, template):
    # check img type
    if type(img) is not str:
        img = img
    else:
        if img.endswith('.mrc'):
            with mrcfile.open(img, permissive=True) as mrc:
                img = mrc.data
        if img.endswith('.png'):
            img = cv2.imread(img, 0)

    img = cv2.normalize(img, None, 0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    img[img > 1.0] = 1.0
    img[img < -1.0] = -1.0
    img_int = img_as_ubyte(img)
    ret, thresh = cv2.threshold(img_int, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    thresh[0:15, :] = 0
    thresh[:, :15] = 0
    thresh[-15:, :] = 0
    thresh[:, -15:] = 0
    thick = False
    bright = None
    contaminated = None
    broken = None
    fractioned = None
    cracked = None
    chull = convex_hull_image(thresh)
    threshed = img_int[chull]
    mean_threshed = np.mean(threshed)
    area = np.sum(chull)
    if area > 1600:
        if mean_threshed < 122.5:
            bright = False
        else:
            bright = True
    else:
        thick = True
    if not thick:
        if not bright:
            # first determine if it is fractioned
            if np.sum(chull) > 13000:
                fractioned = True
            else:
                chull_num = chull.astype(int)*255.0
                contours, h = cv2.findContours(chull_num.astype(np.uint8), 1, 2)
                cnt = contours[0]
                approx = cv2.approxPolyDP(cnt, 0.12*cv2.arcLength(cnt, True), True)
                if len(approx) != 4:
                    fractioned = True
                else:
                    fractioned = False
            # then determine if it is contaminated
            if not fractioned:
                X_plot = np.linspace(0, 255, 500)[:, np.newaxis]
                kde = KernelDensity(kernel='gaussian', bandwidth=6.0).fit(threshed.reshape(-1, 1))
                log_dens = kde.score_samples(X_plot)
                smoothed = smooth(np.exp(log_dens))
                markers_on = find_peaks(smoothed, scale=15)
                markers_on = list(markers_on)
                contam_check = []
                for i in markers_on:
                    if X_plot[i] < 100:
                        contam_check.append(i)
                if len(contam_check) == 1:
                    pass
                elif len(contam_check) == 2:
                    if smoothed[contam_check[0]] < smoothed[contam_check[1]]:
                        if abs(contam_check[0] - contam_check[1]) < 65:
                            if smoothed[contam_check[0]]/smoothed[contam_check[1]] < 0.5:
                                contam_check = contam_check[1:]
                        else:
                            if smoothed[contam_check[0]] < 0.003:
                                contam_check = contam_check[1:]
                    else:
                        if smoothed[contam_check[1]]/smoothed[contam_check[0]] < 0.25:
                            contam_check = contam_check[:-1]

                elif len(contam_check) == 3:
                    if smoothed[contam_check[-1]] < smoothed[contam_check[1]]:
                        if smoothed[contam_check[-1]]/smoothed[contam_check[1]] < 0.2:
                            contam_check = contam_check[:-1]
                        elif smoothed[contam_check[-1]]/smoothed[contam_check[0]] < 0.2:
                            contam_check = contam_check[:-1]
                else:
                    contam_check = contam_check[:2]
                if len(contam_check) == 2:
                    if smoothed[contam_check[0]] < smoothed[contam_check[1]]:
                        if smoothed[contam_check[0]] < 0.003:
                            contam_check = contam_check[1:]
                    else:
                        if smoothed[contam_check[1]]/smoothed[contam_check[0]] < 0.25:
                            contam_check = contam_check[:-1]
                elif len(contam_check) == 3:
                    if smoothed[contam_check[-1]] < smoothed[contam_check[1]]:
                        if smoothed[contam_check[-1]]/smoothed[contam_check[1]] < 0.2:
                            contam_check = contam_check[:-1]
                        elif smoothed[contam_check[-1]]/smoothed[contam_check[0]] < 0.2:
                            contam_check = contam_check[:-1]
                else:
                    contam_check = contam_check[:2]
                if len(contam_check) > 1:
                    contaminated = True
                else:
                    contaminated = False
                if not contaminated:
                    # check if its cracked
                    filtered = cv2.GaussianBlur(img_int, (5, 5), 0)
                    ret_f, thresh_f = cv2.threshold(filtered, 140, 255, cv2.THRESH_BINARY)
                    kernel = np.ones((5, 5), np.uint8)
                    closing = cv2.morphologyEx(thresh_f, cv2.MORPH_CLOSE, kernel)
                    if np.sum(closing)/255 > 8:
                        cracked = True
                    else:
                        cracked = False
        if bright:
            # first detect if it is broken
            ret2, thresh2 = cv2.threshold(img_int, 245, 255, cv2.THRESH_BINARY)
            kernel = np.ones((5, 5), np.uint8)
            closing = cv2.morphologyEx(thresh2, cv2.MORPH_CLOSE, kernel)
            chull2 = convex_hull_image(thresh2)
            if np.sum(chull2) > 15000:
                broken = True
            elif np.sum(thresh2)/255 > 550:
                broken = True
            elif (np.sum(closing)/255)/(np.sum(chull)) > 0.97:
                broken = True
            else:
                broken = False
            if not broken:
                # check if its fractioned
                chull_num = chull.astype(int)*255.0
                contours, h = cv2.findContours(chull_num.astype(np.uint8), 1, 2)
                cnt = contours[0]
                approx = cv2.approxPolyDP(cnt, 0.12*cv2.arcLength(cnt, True), True)
                if len(approx) != 4:
                    fractioned = True
                else:
                    fractioned = False
                # check if it is contaminated
                if not fractioned:

                    X_plot = np.linspace(0, 255, 255)[:, np.newaxis]
                    kde = KernelDensity(kernel='gaussian', bandwidth=4.5).fit(threshed.reshape(-1, 1))
                    log_dens = kde.score_samples(X_plot)
                    smoothed = smooth(np.exp(log_dens))
                    markers_on = find_peaks(smoothed, scale=15)
                    markers_on = list(markers_on)
    # print(markers_on)
                    contam_check = []
                    for i in markers_on:
                        if X_plot[i] < 55 and i != 0:
                            if smoothed[i] > 0.0015:
                                contam_check.append(i)
                    if len(contam_check) > 0:
                        # print(markers_on)
                        contaminated = True
                    elif round(np.sum(smoothed[20:100]), 4) > 0.04 and np.std(threshed) > 34 and np.mean(threshed) > 140:
                        contaminated = True
                    else:
                        contaminated = False
                    # check if its cracked
                    if not contaminated:
                        # print(np.max(smoothed))
                        if type(template) is str:

                            template = np.load(template)

                        res = cv2.matchTemplate(img_int, template, cv2.TM_CCOEFF_NORMED)
                        contam_check = []
                        for i in markers_on:
                            if X_plot[i] > 200 and i < 255:
                                if np.max(res) > 0.89:
                                    if smoothed[i] > 0.0075 and abs(smoothed[i] - np.max(smoothed)) > 0.0001:
                                        if np.argmax(smoothed) > 90 and np.argmax(smoothed) < 105:
                                            pass
                                        else:
                                            contam_check.append(i)
                                else:
                                    if smoothed[i] > 0.0015 and abs(smoothed[i] - np.max(smoothed)) > 0.0001:
                                        if np.argmax(smoothed) > 90 and np.argmax(smoothed) < 105:
                                            pass
                                        else:
                                            contam_check.append(i)
                        if len(contam_check) >= 1:
                            cracked = True
                        elif np.max(smoothed) > 0.04 and np.argmax(smoothed) > 235:
                            cracked = True
                        else:
                            cracked = False

    if thick:
        quality = 'bad'
    elif cracked:
        quality = 'cracked'
    elif broken:
        quality = 'broken'
    elif contaminated:
        quality = 'contaminated'
    elif fractioned:
        quality = 'fractioned'
    else:
        quality = 'good'

    return quality
