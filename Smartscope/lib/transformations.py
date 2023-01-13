import numpy as np
import logging
from math import radians, cos
from scipy.spatial.distance import cdist
from random import random

logger = logging.getLogger(__name__)

def closest_node(node, nodes, num=1):
    nodes = np.stack((nodes))
    cd = cdist(node, nodes)
    index = cd.argmin()
    dist = nodes[index] - node
    return index, dist

def rotate_axis(coord, angle):
    theta = np.radians(angle)
    c, s = np.cos(theta), np.sin(theta)
    R = np.array(((c, -s), (s, c)))
    rotated = np.sum(R * np.reshape(coord, (-1, 1)), axis=0)
    return rotated

def pixel_to_stage(dist, tile, tiltAngle=0):
    apix = tile.PixelSpacing / 10_000
    dist *= apix
    specimen_dist = rotate_axis(dist,tile.RotationAngle)
    coords = tile.StagePosition + specimen_dist / np.array([1, cos(radians(round(tiltAngle, 1)))])
    return np.around(coords, decimals=3)

def register_stage_to_montage(targets_stage_coords:np.ndarray,center_stage_coords:np.ndarray,center_pixel_coords:np.ndarray,apix:float,rotation_angle:float):
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
    pixel_coords = np.apply_along_axis(rotate_axis, 1, stage_pixel_coords, angle=rotation_angle)
    centered_pixel_coords = pixel_coords + center_pixel_coords
    return centered_pixel_coords

def register_targets_by_proximity(targets:np.array, new_targets:np.array):
    distance_matrix = cdist(targets,new_targets)
    closest_index = np.argmin(distance_matrix,1)
    return closest_index

def add_IS_offset(hole_size_in_um: float, mesh_type: str, offset_in_um: float = -1) -> float:
    if offset_in_um != -1:
        return offset_in_um
    hole_radius = hole_size_in_um / 2
    max_offset_factor = 0.5
    if mesh_type == 'Carbon':
        max_offset_factor = 0.8
    offset_in_um = round(random() * hole_radius * max_offset_factor, 1)
    logger.info(f'Adding a {offset_in_um} \u03BCm offset to sample ice gradient along the hole.')
    return offset_in_um