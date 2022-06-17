import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'detectors'))

from .detectors.detect_squares import detect
from .detectors.detect_holes import detect_holes, detect_and_classify_holes
from ..basic_finders import find_square_center
import logging
import torch
# logger = logging.getLogger('processing')
# logger = logging.getLogger('autoscreen')
logger = logging.getLogger(__name__)

WEIGHT_DIR = os.path.join(os.getenv("TEMPLATE_FILES"), 'weights')
IS_CUDA = torch.cuda.is_available()


def find_squares(montage, **kwargs):
    logger.info('Running AI find_squares')
    kwargs['weights'] = os.path.join(WEIGHT_DIR, kwargs['weights'])
    if not IS_CUDA:
        kwargs['device'] = 'cpu'
    squares, labels, _, _ = detect(montage.raw_montage, **kwargs)
    success = True
    if len(squares) < 20 and montage.raw_montage.shape[0] > 20000:
        success = False
    logger.info(f'AI square finder found {len(squares)} squares')
    logger.debug(f'{squares},{type(squares)}')
    return (squares, labels), success, 'AISquareTarget', None


def find_holes(montage, **kwargs):
    logger.info('Running AI hole detection')
    centroid = find_square_center(montage.raw_montage)
    kwargs['weights_circle'] = os.path.join(WEIGHT_DIR, kwargs['weights_circle'])
    if not IS_CUDA:
        kwargs['device'] = 'cpu'
    holes, _ = detect_holes(montage.raw_montage, **kwargs)
    success = True
    if len(holes) < 10:
        success = False

    logger.info(f'AI hole detection found {len(holes)} holes')
    return holes, success, 'AIHoleTarget', centroid


def find_and_classify_holes(montage, **kwargs):
    logger.info('Running AI hole detection and classification')
    centroid = find_square_center(montage.raw_montate)
    holes, labels = detect_and_classify_holes(montage.raw_montage, **kwargs)
    # print(holes)
    success = True
    if len(holes) < 20:
        success = False

    logger.info(f'AI hole detection found {len(holes)} holes')
    return (holes, labels), success, 'AIHoleTarget', centroid
