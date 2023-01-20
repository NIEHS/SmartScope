import numpy as np
import time
from pathlib import Path
from Smartscope.lib.image_manipulations import auto_contrast_sigma
import imutils
import cv2
import logging

logger = logging.getLogger(__name__)

def generate_diagnostic_figure(image:np.array, coords_set, outputpath:Path):
    image = auto_contrast_sigma(image)
    image_color = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    for coords, color, perc_im_radius in coords_set:
        radius = int(image_color.shape[0]*(perc_im_radius/100))
        for coord in coords:
            cv2.circle(image_color,coord,radius,color=color, thickness=cv2.FILLED)
    cv2.imwrite(str(outputpath), imutils.resize(image_color,512))


class Timer:
    description_text:str

    def __init__(self, text:str):
        self.description_text = text

    def __enter__(self):
        logger.debug(f'Timer for {self.description_text} started')
        self.start = time.time()
        self.latest_timestamp = self.start
        return self

    def report_timer(self, text):
        current_time = time.time()
        timer = current_time - self.latest_timestamp
        total = current_time - self.start
        logger.debug(f'Step {text} took {timer:.2f} seconds. Total time elapsed: {total:.2f} seconds ')
        self.latest_timestamp = current_time

    def __exit__(self, exception_type, exception_value, traceback):
        timer = time.time() - self.start
        logger.debug(f'{self.description_text} took {timer:.2f} seconds to run.')
