import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'detectors'))

from .detectors.detect_squares import detect
from .detectors.detect_holes import detect_holes, detect_and_classify_holes
from ..basic_finders import find_square_center
import logging

proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')

WEIGHT_DIR = os.path.join(os.getenv("TEMPLATE_FILES"), 'weights')


def find_squares(montage, **kwargs):
    proclog.info('Running AI find_squares')
    kwargs['weights'] = os.path.join(WEIGHT_DIR, kwargs['weights'])
    squares, labels, _, _ = detect(montage.raw_montage, **kwargs)
    success = True
    if len(squares) < 20 and montage.raw_montage.shape[0] > 20000:
        success = False
    proclog.info(f'AI square finder found {len(squares)} squares')
    proclog.debug(f'{squares},{type(squares)}')
    return (squares, labels), success, 'AISquareTarget', None


def find_holes(montage, **kwargs):
    proclog.info('Running AI hole detection')
    centroid = find_square_center(montage.raw_montage)
    kwargs['weights_circle'] = os.path.join(WEIGHT_DIR, kwargs['weights_circle'])
    holes, _ = detect_holes(montage.raw_montage, **kwargs)
    success = True
    if len(holes) < 10:
        success = False

    proclog.info(f'AI hole detection found {len(holes)} holes')
    return holes, success, 'AIHoleTarget', centroid


def find_and_classify_holes(montage, **kwargs):
    proclog.info('Running AI hole detection and classification')
    centroid = find_square_center(montage.raw_montate)
    holes, labels = detect_and_classify_holes(montage.raw_montage, **kwargs)
    # print(holes)
    success = True
    if len(holes) < 20:
        success = False

    proclog.info(f'AI hole detection found {len(holes)} holes')
    return (holes, labels), success, 'AIHoleTarget', centroid
