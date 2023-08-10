import numpy as np
import logging
from scipy.spatial.distance import cdist
from Smartscope.lib.image.process_image import ProcessImage


logger = logging.getLogger(__name__)

def register_to_other_montage(
        coords,
        center_coords,
        montage,
        parent_montage,
        extra_angle=0
    ):
    centered_coords =  coords - center_coords
    scale = parent_montage.pixel_size / montage.pixel_size
    scaled_coords = centered_coords * scale 
    delta_rotation = parent_montage.rotation_angle - montage.rotation_angle + extra_angle
    logger.debug(f'''
        Image Rotation = {montage.rotation_angle}
        Parent Rotation = {parent_montage.rotation_angle}
        Delta = {parent_montage.rotation_angle - montage.rotation_angle}
        Currently testing = {delta_rotation}
    ''')
    pixel_coords = np.apply_along_axis(ProcessImage.rotate_axis, 1,
        scaled_coords, angle=delta_rotation)
    centered_pixel_coords = pixel_coords + montage.center
    return centered_pixel_coords

def register_stage_to_montage(
        targets_stage_coords:np.ndarray,
        center_stage_coords:np.ndarray,
        center_pixel_coords:np.ndarray,
        apix:float,
        rotation_angle:float
    ):
    """Converts stage coordinates calculated at a given magnification to another magnification image. 
    i.e. Draw holes found at low SA on the Atlas or vice-versa

    Args:
        targets_stage_coords (np.ndarray): 2-D array of stage or specimen x,y coordinates in microns where each line is a coordinate pair
        center_stage_coords (np.ndarray): x,y stage or specimen coordinates of the image where the targets are to be registered
        center_pixel_coords (np.ndarray): x,y pixel coordinates of the center_stage_coords argument
        apix (float): Pixel size in Angstrom per pixel of the image where the targets are being registered
        rotation_angle (float): Rotation angle of the tilt axis of the image where the targets are being registered
    """
    centered_stage_coords = targets_stage_coords - center_stage_coords
    stage_pixel_coords = np.array(centered_stage_coords) / (apix/10_000)
    pixel_coords = np.apply_along_axis(ProcessImage.rotate_axis, 1,
        stage_pixel_coords, angle=rotation_angle)
    centered_pixel_coords = pixel_coords + center_pixel_coords
    return centered_pixel_coords


# def rotate_axis(coord, angle):
#     theta = np.radians(angle)
#     c, s = np.cos(theta), np.sin(theta)
#     R = np.array(((c, -s), (s, c)))
#     rotated = np.sum(R * np.reshape(coord, (-1, 1)), axis=0)
#     return rotated
    
def register_targets_by_proximity(
        targets:np.array,
        new_targets:np.array
    ):
    distance_matrix = cdist(targets,new_targets)
    closest_index = np.argmin(distance_matrix,1)
    return closest_index

