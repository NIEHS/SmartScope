import numpy as np
from pathlib import Path
from Smartscope.lib.image_manipulations import auto_contrast_sigma
import imutils
import cv2

def generate_diagnostic_figure(image:np.array, coords_set, outputpath:Path):
    image = auto_contrast_sigma(image)
    image_color = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    for coords, color, perc_im_radius in coords_set:
        radius = int(image_color.shape[0]*(perc_im_radius/100))
        for coord in coords:
            cv2.circle(image_color,coord,radius,color=color, thickness=cv2.FILLED)
    cv2.imwrite(str(outputpath), imutils.resize(image_color,512))